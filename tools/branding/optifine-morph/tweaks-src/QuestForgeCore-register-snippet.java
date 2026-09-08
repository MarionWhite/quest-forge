// If/when a JDK exists and the work-folder Morph jar has been playtested,
// add MorphOptifineTransformer to QuestForgeCore.getASMTransformerClass:
//
//     return new String[] {
//         "com.questforge.PanelButtonQuestTransformer",
//         "com.questforge.MorphOptifineTransformer"
//     };
//
// Copy MorphHandGuard.java + MorphOptifineTransformer.java next to the
// existing questforge-coremod sources, add them to build.bat's javac
// list, and rebuild. Do NOT run build.bat until then — it installs
// into live mods\.
//
// The work-folder Morph jar is self-contained and does not need this.
