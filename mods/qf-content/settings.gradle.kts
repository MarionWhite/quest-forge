rootProject.name = "QuestForgeContent"

pluginManagement {
  repositories {
    maven {
      // RetroFuturaGradle lives here, not on Maven Central
      name = "GTNH Maven"
      url = uri("https://nexus.gtnewhorizons.com/repository/public/")
      mavenContent {
        includeGroupByRegex("com\\.gtnewhorizons\\..+")
        includeGroup("com.gtnewhorizons")
      }
    }
    gradlePluginPortal()
    mavenCentral()
    mavenLocal()
  }
}

plugins {
  // Lets Gradle find/download the Java 8 toolchain automatically
  id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}
