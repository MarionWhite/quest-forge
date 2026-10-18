// Quest Forge runs only on Angelica's Iris backport (docs/design/shaders/README.md,
// "Platform stance"). On OptiFine E7 this stops the compile, and OptiFine falls back to
// no shaders. Every program includes this file first.
#ifndef IS_ANGELICA
#error "Quest Forge shaders need the Angelica client (Iris on 1.7.10). OptiFine is not supported."
#endif
