// Imported rather than written out at the use site: in a Kotlin build script `java`
// resolves to the Java plugin's extension, which shadows the package of the same
// name, so `java.util.zip.ZipFile` does not compile.
import java.util.zip.ZipFile

plugins {
  id("java-library")
  id("com.gtnewhorizons.retrofuturagradle") version "2.0.3"
}

group = "com.questforge.content"
version = "1.0.0"

java {
  toolchain {
    // Compile against Java 8. Azul is the only vendor shipping a Java 8 JDK for
    // macOS arm64 -- and 8u442 is already installed on this machine.
    languageVersion.set(JavaLanguageVersion.of(8))
    vendor.set(org.gradle.jvm.toolchain.JvmVendorSpec.AZUL)
  }
}

// Several sources contain the section sign that Minecraft uses for colour codes.
// Without this javac reads them in the platform default encoding -- UTF-8 on this
// Mac, but windows-1252 on a Windows machine -- so the same source would compile to
// different string constants depending on who built it, and the colour codes would
// come out as mojibake in game.
tasks.withType<JavaCompile>().configureEach {
  options.encoding = "UTF-8"
}

minecraft {
  mcVersion.set("1.7.10")
  username.set("Developer")
  injectedTags.put("VERSION", project.version)

  // In a dev workspace there is no jar manifest for FML to read, so the coremod
  // has to be named explicitly or the Container.slotClick transformer never runs
  // and drag-and-drop silently does nothing.
  extraRunJvmArguments.add("-Dfml.coreMods.load=com.questforge.content.core.QFLoadingPlugin")
}

tasks.injectTags.configure {
  outputClassName.set("${project.group}.Tags")
}

// src/test/java holds CookbookExamples.java, which exists purely so the compiler
// checks every snippet in COOKBOOK.md. There are no JUnit tests, and Gradle 9
// treats "test sources but no tests" as an error unless told otherwise.
tasks.test.configure {
  failOnNoDiscoveredTests.set(false)
}

// Verifies the ASM transformers offline, against the real Minecraft classes.
//
// Worth having because two of the three patched classes only load once you are in
// a world, so a broken patch would otherwise stay invisible until several minutes
// into a manual test -- and a bad patch fails as a VerifyError, not a compile error.
tasks.register<JavaExec>("checkTransformers") {
  group = "verification"
  description = "Runs every ASM transformer against real Minecraft classes and verifies the output"
  mainClass.set("TransformerCheck")
  classpath = sourceSets.test.get().runtimeClasspath
  dependsOn(tasks.testClasses)
}

// Round-trips the voice codec and measures the error.
//
// Worth having for the same reason as the transformer check: a wrong constant in the
// ADPCM tables does not throw, does not fail to decode, and does not look wrong in
// any log -- it just quietly degrades everyone's audio, and noticing by ear requires
// already suspecting it. It also pins the per-frame predictor seed in place, since
// dropping that still sounds perfect until the first lost frame.
tasks.register<JavaExec>("checkVoiceCodec") {
  group = "verification"
  description = "Round-trips the voice codec and checks SNR and recovery from frame loss"
  mainClass.set("VoiceCodecCheck")
  classpath = sourceSets.test.get().runtimeClasspath
  dependsOn(tasks.testClasses)
}

// Checks the built jar can decode mp3 and Ogg with nothing else on the classpath.
//
// Worth having because this is the one failure the dev client structurally cannot
// show: there the decoders are on the system classpath, so the game plays music
// whatever the jar contains. Only a packed instance has just the jar, so without this
// the first evidence of a bad shade is somebody's music not working.
//
// The classpath is deliberately the jar plus the compiled check and nothing else --
// adding the project's own dependencies would prop the jar up and pass regardless.
tasks.register<JavaExec>("checkShadedAudio") {
  group = "verification"
  description = "Runs the built jar alone and checks both audio decoders are reachable"
  mainClass.set("ShadedAudioCheck")
  classpath = files(tasks.jar.flatMap { it.archiveFile }, sourceSets.test.get().output)
  dependsOn(tasks.jar, tasks.testClasses)
}

// So `./gradlew build` cannot produce a jar whose bytecode patches are broken.
tasks.check.configure {
  dependsOn("checkTransformers")
  dependsOn("checkVoiceCodec")
  dependsOn("checkShadedAudio")
}

// ---------------------------------------------------------------------------
// Shading the audio decoders into the built jar.
//
// The mod's jukebox reads mp3 and ogg through javax.sound.sampled, which finds its
// decoders by scanning every META-INF/services/javax.sound.sampled.spi.* file on the
// classpath. In the dev client those files arrive inside the dependency jars and
// everything works; a plain `jar` task ships none of it, so the same code in the real
// pack throws UnsupportedAudioFileException on the first track.
//
// Copying the dependencies in is not enough either, and this is the part that bites:
// mp3spi and vorbisspi each declare the SAME TWO service files. Any shade that
// resolves that collision by picking a winner -- which is what every duplicate
// strategy short of merging does -- produces a jar that plays exactly one of the two
// formats, and the loss is silent. So they are merged line by line here.
//
// The staging directory is exploded by this task rather than handed to the jar as a
// zipTree, because zipTree is a Project API and calling it while the jar is being
// built breaks the configuration cache.
// ---------------------------------------------------------------------------

abstract class ShadeLibraries : DefaultTask() {

    @get:InputFiles
    abstract val libraries: ConfigurableFileCollection

    @get:OutputDirectory
    abstract val destination: DirectoryProperty

    @TaskAction
    fun shade() {
        val out = destination.get().asFile
        out.deleteRecursively()
        out.mkdirs()

        // Insertion-ordered, so the merged file is stable from build to build and a
        // diff of two jars stays readable.
        val services = linkedMapOf<String, LinkedHashSet<String>>()
        var classes = 0

        libraries.files.filter { it.isFile }.sortedBy { it.name }.forEach { jar ->
            ZipFile(jar).use { zip ->
                zip.entries().toList().filterNot { it.isDirectory }.forEach { entry ->
                    val name = entry.name

                    if (name.startsWith("META-INF/services/")) {
                        val service = name.substringAfterLast('/')
                        if (service.isNotEmpty()) {
                            val lines = zip.getInputStream(entry).bufferedReader()
                                .readLines()
                                .map { it.substringBefore('#').trim() }
                                .filter { it.isNotEmpty() }
                            services.getOrPut(service) { linkedSetOf() }.addAll(lines)
                        }
                        return@forEach
                    }

                    // The signatures cover the original jar and are invalid over
                    // ours; leaving them in makes the JVM reject the classes.
                    if (name == "META-INF/MANIFEST.MF" ||
                        name.endsWith(".SF") || name.endsWith(".DSA") ||
                        name.endsWith(".RSA") || name == "module-info.class") {
                        return@forEach
                    }

                    val target = File(out, name)
                    target.parentFile.mkdirs()
                    zip.getInputStream(entry).use { input ->
                        target.outputStream().use { input.copyTo(it) }
                    }
                    if (name.endsWith(".class")) classes++
                }
            }
        }

        val serviceDir = File(out, "META-INF/services")
        serviceDir.mkdirs()
        services.forEach { (service, providers) ->
            File(serviceDir, service).writeText(providers.joinToString("\n", postfix = "\n"))
        }

        // Printed rather than assumed. A merge that quietly kept one provider looks
        // exactly like a merge that kept both until someone plays the wrong format.
        logger.lifecycle("Shaded $classes classes from ${libraries.files.size} libraries")
        services.forEach { (service, providers) ->
            logger.lifecycle("  $service -> ${providers.size} provider(s)")
            providers.forEach { logger.lifecycle("      $it") }
        }
    }
}

// A configuration of its own, so the jar takes exactly these and not the whole
// runtime classpath -- which under RetroFuturaGradle includes Minecraft itself.
val shade: Configuration by configurations.creating {
    isCanBeConsumed = false
    isCanBeResolved = true
}
configurations.implementation.get().extendsFrom(shade)

val shadeLibraries = tasks.register<ShadeLibraries>("shadeLibraries") {
    group = "build"
    description = "Explodes the audio decoders and merges their service files"
    libraries.from(shade)
    destination.set(layout.buildDirectory.dir("shaded"))
}

// This jar is both a coremod and a mod. The coremod half exists only to inject a
// hook into Container.slotClick, which Forge 1.7.10 gives no event for.
//
// The marker attribute is "FMLCorePluginContainsFMLMod" -- note the FML in the
// middle. See CoreModManager line 60. Without it (or misspelled as the more
// obvious "FMLCorePluginContainsMod") FML loads the coremod, runs the
// transformer, and then SILENTLY skips the jar during mod discovery: the patch
// applies but the @Mod never loads. The log line to look for is
// "Skipping already parsed coremod or tweaker".
tasks.jar.configure {
  manifest {
    attributes(
      mapOf(
        "FMLCorePlugin" to "com.questforge.content.core.QFLoadingPlugin",
        "FMLCorePluginContainsFMLMod" to "true"
      )
    )
  }

  from(shadeLibraries)
}

tasks.processResources.configure {
  val projVersion = project.version.toString()
  inputs.property("version", projVersion)
  filesMatching("mcmod.info") {
    expand(mapOf("modVersion" to projVersion))
  }
}

// ---------------------------------------------------------------------------
// Running the dev client on this Mac.
//
// Forge 1.7.10 NPEs in ClassPatchManager on any Java 8 newer than ~8u242, and
// LWJGL 2 additionally dies with "NSWindow geometry should only be modified on
// the main thread" on those builds. The Zulu 8u442 toolchain above is fine for
// COMPILING but cannot RUN the game, so the run tasks are pinned to the Oracle
// 8u162 x86_64 JDK (via Rosetta), which is the same JVM the Prism instance uses.
// ---------------------------------------------------------------------------
// The dev client deliberately runs on the SAME arm64 Zulu 8 toolchain used for
// compiling, i.e. RFG's default -- no override here.
//
// This differs from the Prism instance, which must use Oracle 8u162 x86_64.
// The reason is that RFG ships arm64 LWJGL natives and extracts them into
// run/natives/lwjgl2. Forcing an x86_64 JVM here fails at startup with:
//   UnsatisfiedLinkError: liblwjgl.dylib (have 'arm64', need 'x86_64')
// RFG also patches Minecraft at build time, so the runtime ClassPatchManager
// path that breaks the packed instance on newer Java 8 is not exercised here.

repositories {
  maven {
    name = "GTNH Maven"
    url = uri("https://nexus.gtnewhorizons.com/repository/public/")
  }
  mavenCentral()
}

// Dev-client-only dependencies: present in runClient, never bundled into the jar
// and never a dependency of the built mod.
val runtimeOnlyNonPublishable: Configuration by configurations.creating {
  description = "Runtime only dependencies that are not published alongside the jar"
  isCanBeConsumed = false
  isCanBeResolved = false
}
listOf(configurations.runtimeClasspath, configurations.testRuntimeClasspath).forEach {
  it.configure { extendsFrom(runtimeOnlyNonPublishable) }
}

dependencies {
  // NEI in the dev client, so you can browse your items and check recipes without
  // launching the whole pack. This is the GTNH fork (the only one published with a
  // :dev classifier); the pack itself ships stock NEI, which is fine -- this copy
  // never leaves the dev environment.
  runtimeOnlyNonPublishable("com.github.GTNewHorizons:NotEnoughItems:2.8.130-GTNH:dev")

  // To write code against a mod that is in the pack, drop its jar in libs/ and:
  // implementation(rfg.deobf(project.files("libs/SomeMod.jar")))

  // Audio decoders for the jukebox. Java 8 decodes only WAV/AIFF/AU natively, and
  // an album in WAV is gigabytes, so real music needs these.
  //
  // Both register themselves with javax.sound.sampled through META-INF/services,
  // which means AudioSystem.getAudioInputStream() simply starts understanding mp3
  // and ogg -- DirectAudio.FileSource needs no changes at all.
  //
  // Declared against `shade`, which `implementation` extends: the compiler and the
  // dev client see them as normal dependencies, and the built jar additionally gets
  // their classes with the service files merged. See ShadeLibraries above for why
  // merging rather than copying is the whole point.
  //
  // Both are LGPL, unmodified. Attribution ships in META-INF/AUDIO-LIBRARIES.txt.
  shade("com.googlecode.soundlibs:mp3spi:1.9.5.4")
  shade("com.googlecode.soundlibs:vorbisspi:1.0.3.3")
}

// Lets the dev server be driven from a terminal or a pipe.
//
// Gradle's JavaExec leaves stdin detached, so a dedicated server started with
// runServer cannot be sent a single command -- which makes it useless for
// exercising anything that is triggered by one. The census is: it has to be
// possible to run it headlessly and check the output, rather than only ever
// finding out whether it works by loading the whole pack by hand.
tasks.matching { it.name == "runServer" }.configureEach {
  (this as JavaExec).standardInput = System.`in`
}
