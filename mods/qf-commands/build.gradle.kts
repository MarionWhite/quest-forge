// QuestForgeCommands -- unlockable player commands, earned rather than granted.
//
// Deliberately small and dependency-free: it does not need qf-content, and
// nothing in the pack needs it. Kept as its own project so it can be dropped
// into another instance on its own.
//
// The build is the same shape as mods/transformers -- same RFG version, same
// toolchain reasoning, same machine-local gradle.properties. See
// docs/development/building-on-windows.md.

plugins {
  id("java-library")
  id("com.gtnewhorizons.retrofuturagradle") version "2.0.3"
}

group = "com.questforge.commands"
version = "1.0.0"

java {
  toolchain {
    // Java 8 bytecode, because the game runs on 8. Which vendor's Java 8 is a
    // property of the machine and not of this project, so it is a property:
    // set qfJava8Vendor=any in ~/.gradle/gradle.properties on a box that has
    // something other than Azul, which is every Windows machine here.
    languageVersion.set(JavaLanguageVersion.of(8))
    val vendorName = (findProperty("qfJava8Vendor") as String? ?: "azul").lowercase()
    if (vendorName != "any") {
      vendor.set(when (vendorName) {
        "azul"                 -> JvmVendorSpec.AZUL
        "oracle"               -> JvmVendorSpec.ORACLE
        "temurin", "adoptium"  -> JvmVendorSpec.ADOPTIUM
        "corretto", "amazon"   -> JvmVendorSpec.AMAZON
        "microsoft"            -> JvmVendorSpec.MICROSOFT
        "semeru", "ibm"        -> JvmVendorSpec.IBM
        "graalvm"              -> JvmVendorSpec.GRAAL_VM
        "liberica", "bellsoft" -> JvmVendorSpec.BELLSOFT
        "sap"                  -> JvmVendorSpec.SAP
        else -> throw GradleException(
          "Unknown qfJava8Vendor '$vendorName'. Use one of: any, azul, oracle, " +
          "temurin, corretto, microsoft, semeru, graalvm, liberica, sap.")
      })
    }
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

tasks.processResources.configure {
  val projVersion = project.version.toString()
  inputs.property("version", projVersion)
  filesMatching("mcmod.info") {
    expand(mapOf("modVersion" to projVersion))
  }
}
