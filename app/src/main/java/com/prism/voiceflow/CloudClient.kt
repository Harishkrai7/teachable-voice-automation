package com.prism.voiceflow

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class CloudClient(baseUrl: String, private val apiKey: String?) {
    private val base = baseUrl.trim().trimEnd('/')
    private val gson = Gson()
    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .build()
    private val json = "application/json; charset=utf-8".toMediaType()

    private fun builder(path: String) = Request.Builder().url(base + path).apply {
        if (!apiKey.isNullOrBlank()) header("X-API-Key", apiKey)
    }

    private suspend fun <T> post(path: String, body: Any, cls: Class<T>): T = withContext(Dispatchers.IO) {
        val req = builder(path).post(gson.toJson(body).toRequestBody(json)).build()
        http.newCall(req).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) throw IOException("HTTP ${resp.code}: ${text.take(300)}")
            gson.fromJson(text, cls)
        }
    }

    suspend fun health(): String = withContext(Dispatchers.IO) {
        http.newCall(builder("/health").get().build()).execute().use { resp ->
            if (!resp.isSuccessful) throw IOException("HTTP ${resp.code}")
            resp.body?.string().orEmpty()
        }
    }

    suspend fun teach(r: TeachRequest) = post("/v1/teach", r, TeachResponse::class.java)
    suspend fun replay(r: ReplayRequest) = post("/v1/replay", r, ReplayResponse::class.java)
    suspend fun stepResult(r: StepResultRequest) = post("/v1/step-result", r, StepResultResponse::class.java)
}
