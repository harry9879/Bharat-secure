# Vosk talks to native code through JNA reflection.
-keep class com.sun.jna.** { *; }
-keep class org.vosk.** { *; }
-dontwarn java.awt.**
