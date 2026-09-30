plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.samsung.prism.automation"
    compileSdk = 34

  defaultConfig {
    applicationId = "com.prism.voiceflow"
    minSdk = 26
    targetSdk = 34
    versionCode = 1
    versionName = "0.1-mvp"

    buildConfigField(
        "String",
        "BASE_URL",
        "\"https://teachable-voice-backend-52478641978.asia-south1.run.app/\""
    )
}

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    implementation("com.google.code.gson:gson:2.11.0")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    implementation("androidx.appcompat:appcompat:1.7.0")
}