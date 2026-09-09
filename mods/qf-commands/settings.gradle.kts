pluginManagement {
  repositories {
    maven {
      name = "GTNH Maven"
      url = uri("https://nexus.gtnewhorizons.com/repository/public/")
    }
    gradlePluginPortal()
    mavenCentral()
  }
}

rootProject.name = "QuestForgeCommands"
