// The version of an in-house mod, derived from git. Applied by qf-content and
// qf-commands (qf-tweaks has no Gradle; build.bat computes the same string).
//
//     1.1.0+20261017.86eef67a          last commit that touched this mod's directory
//     1.1.0+20261017.86eef67a.dirty    built with uncommitted changes in it
//     1.1.0+unknown                    no git (a source zip): never matches a real build
//
// Why it matters: FML's login handshake compares mod versions as plain strings
// (NetworkModHolder.acceptVersion is String.equals when a mod declares no
// acceptableRemoteVersions). Every in-house mod used to say 1.0.0 forever, so a
// September client passed the handshake against an October server. With a
// per-commit version, a stale qf-content is refused at the handshake.
//
// Only the mod's own directory counts, so a docs-only commit does not force every
// friend to update. Config changes are caught separately, by the pack fingerprint
// (qf-content's packcheck).
//
// The sha is cut to 8 characters here rather than by git's %h, whose length depends
// on how many objects the clone has; a Mac and a Windows clone of the same commit
// must produce the same version or they would refuse each other.
//
// The JAR FILE NAME does not change (archiveVersion stays 1.0.0 in each build): an
// update has to overwrite the old jar, not sit next to it as a second copy of the mod.

val qfBaseVersion = "1.1.0"

fun qfGit(vararg args: String): String? = try {
    val out = providers.exec {
        commandLine(listOf("git", "-C", projectDir.absolutePath) + args.toList())
        isIgnoreExitValue = true
    }
    if (out.result.get().exitValue != 0) null
    else out.standardOutput.asText.get().trim().ifEmpty { null }
} catch (e: Exception) {
    null
}

val qfStamp = qfGit("log", "-1", "--format=%cd.%H", "--date=format:%Y%m%d", "--", ".")
version = if (qfStamp == null) {
    "$qfBaseVersion+unknown"
} else {
    val (date, sha) = qfStamp.split('.', limit = 2)
    val dirty = qfGit("status", "--porcelain", "--", ".") != null
    "$qfBaseVersion+$date.${sha.take(8)}" + (if (dirty) ".dirty" else "")
}
