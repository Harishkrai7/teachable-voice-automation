package com.prism.voiceflow

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Isolated Settings screen for server URL and API key.
 * Kept separate from MainActivity so credentials are never displayed
 * during normal usage and can't be shoulder-surfed easily.
 */
class SettingsActivity : Activity() {

    private val scope = MainScope()
    private val prefs by lazy { getSharedPreferences("voiceflow", MODE_PRIVATE) }

    private lateinit var etUrl: EditText
    private lateinit var etApiKey: EditText
    private lateinit var tvConnectionStatus: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        etUrl               = findViewById(R.id.etUrl)
        etApiKey            = findViewById(R.id.etApiKey)
        tvConnectionStatus  = findViewById(R.id.tvConnectionStatus)

        // Pre-fill saved values
        etUrl.setText(prefs.getString("url", ""))
        etApiKey.setText(prefs.getString("key", ""))

        // Back button
        findViewById<android.widget.ImageButton>(R.id.btnBack).setOnClickListener {
            finish()
        }

        // Test connection
        findViewById<Button>(R.id.btnTestConnection).setOnClickListener {
            testConnection()
        }

        // Save
        findViewById<Button>(R.id.btnSave).setOnClickListener {
            saveAndFinish()
        }
    }

    override fun onDestroy() {
        scope.cancel(); super.onDestroy()
    }

    private fun buildClient(): CloudClient {
        val url = etUrl.text.toString().trim()
        val key = etApiKey.text.toString().trim()
        if (url.isBlank()) throw IllegalArgumentException("Server URL is required")
        return CloudClient(url, key)
    }

    private fun testConnection() {
        val client = try { buildClient() } catch (e: Exception) {
            tvConnectionStatus.text = "⚠️ ${e.message}"
            tvConnectionStatus.setTextColor(0xFFFF6B6B.toInt())
            return
        }
        tvConnectionStatus.text = "Connecting…"
        tvConnectionStatus.setTextColor(0xFFAAAACC.toInt())
        scope.launch {
            try {
                val response = client.health()
                tvConnectionStatus.text = "✅ Connected: $response"
                tvConnectionStatus.setTextColor(0xFF66BB6A.toInt())
            } catch (e: Exception) {
                tvConnectionStatus.text = "⚠️ ${e.message}"
                tvConnectionStatus.setTextColor(0xFFFF6B6B.toInt())
            }
        }
    }

    private fun saveAndFinish() {
        val url = etUrl.text.toString().trim()
        val key = etApiKey.text.toString().trim()
        if (url.isBlank()) {
            Toast.makeText(this, "Please enter the server URL", Toast.LENGTH_SHORT).show()
            return
        }
        prefs.edit()
            .putString("url", url)
            .putString("key", key)
            .apply()
        Toast.makeText(this, "Settings saved", Toast.LENGTH_SHORT).show()
        finish()
    }
}
