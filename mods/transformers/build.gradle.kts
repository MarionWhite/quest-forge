// TransformersMod 0.6.x for 1.7.10, ported from its original ForgeGradle 1.2 build.
//
// The upstream build.gradle (kept as build.gradle.orig) cannot run any more: it
// resolves ForgeGradle 1.2-SNAPSHOT and its two mod dependencies from
// files.minecraftforge.net/maven, chickenbones.net/maven and mobiusstrip.eu/maven,
// all three of which are gone -- and all three are plain http, which Gradle now
// refuses regardless. Nothing here changes the mod's own source; only how it is
// compiled. Kept deliberately close to the QuestForge-Mods build so the same
// three-JVM split applies (see gradle.properties).

plugins {
  id("java-library")
  id("com.gtnewhorizons.retrofuturagradle") version "2.0.3"
}

group = "fiskfille.tf"

// Upstream declared 0.6.0 in build.gradle while the source tree is the 0.6.3 line.
// The jar name is what shows up in the mod list and in crash reports, so it says
// which commit this actually is rather than which number the old build claimed.
version = "0.6.3-qf1"

java {
  toolchain {
    languageVersion.set(JavaLanguageVersion.of(8))
    vendor.set(org.gradle.jvm.toolchain.JvmVendorSpec.AZUL)
  }
}

minecraft {
  mcVersion.set("1.7.10")
  username.set("Developer")
}

repositories {
  maven {
    name = "GTNH Maven"
    url = uri("https://nexus.gtnewhorizons.com/repository/public/")
  }
  mavenCentral()
}

dependencies {
  // NEI and Waila are compile-only integration surfaces: fiskfille.tf.nei.*,
  // fiskfille.tf.waila.* and GuiGroundBridge's INEIGuiHandler. Both mods are in
  // the pack, so the integration is worth keeping rather than stripping -- but
  // neither is bundled, and FML loads the optional classes only when the mod is
  // present.
  // Deliberately the PACK'S OWN jars, deobfuscated by RFG, not the GTNH forks
  // from maven. GTNH's NEI generified TemplateRecipeHandler (GuiRecipe<?> where
  // stock NEI has a raw GuiRecipe), so the four recipe handlers here fail to
  // compile against it with "same erasure, yet neither overrides the other" --
  // and had they compiled, they would have been built against signatures the
  // pack does not actually ship. These are the exact jars the game will load.
  compileOnly(rfg.deobf(project.files("libs/NotEnoughItemsuniversal.jar")))
  compileOnly(rfg.deobf(project.files("libs/CodeChickenLib.jar")))
  compileOnly(rfg.deobf(project.files("libs/CodeChickenCore.jar")))
  compileOnly(rfg.deobf(project.files("libs/Waila.jar")))
}

// The upstream build used ForgeGradle's `replace` to substitute the version token
// in TransformersMod.java. RFG has no such hook, so it is done here, on a copy --
// src/ is never written to.
val versionToken = version.toString()

tasks.processResources.configure {
  inputs.property("version", versionToken)
  filesMatching("mcmod.info") {
    expand(mapOf("version" to versionToken))
  }
}

val tokenisedSource = layout.buildDirectory.dir("tokenised-src")

val substituteVersion by tasks.registering(Copy::class) {
  from("src/main/java")
  into(tokenisedSource)
  filesMatching("**/TransformersMod.java") {
    filter { line -> line.replace("\"\${version}\"", "\"$versionToken\"") }
  }
}

sourceSets {
  main {
    java {
      setSrcDirs(listOf(tokenisedSource))
    }
  }
}

tasks.compileJava.configure { dependsOn(substituteVersion) }

// Same coremod manifest as upstream. FMLCorePluginContainsFMLMod is what makes FML
// also load the @Mod half of the jar; without it the transformers run and the mod
// itself is silently skipped.
tasks.jar.configure {
  manifest {
    attributes(
      mapOf(
        "FMLCorePlugin" to "fiskfille.tf.asm.TFLoadingPlugin",
        "FMLCorePluginContainsFMLMod" to "true"
      )
    )
  }
}
