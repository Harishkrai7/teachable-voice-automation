package com.prism.voiceflow

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognizerIntent
import android.text.InputType
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : Activity() {

    private val scope = MainScope()
    private val prefs by lazy { getSharedPreferences("voiceflow", MODE_PRIVATE) }
    private lateinit var urlField: EditText
    private lateinit var keyField: EditText
    private lateinit var cmdField: EditText
    private lateinit var status: TextView
    private var pendingAfterSpeech: ((String) -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (16 * resources.displayMetrics.density).toInt()
        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setPadding(pad, pad, pad, pad)
        }
        fun button(label: String, onClick: () -> Unit) =
            Button(this).apply { text = label; setOnClickListener { onClick() } }.also { col.addView(it) }

        col.addView(TextView(this).apply { text = "Teachable Voice Automation"; textSize = 22f })
        urlField = EditText(this).apply {
            hint = "Server URL, e.g. https://prism-xxxx.a.run.app"
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            setText(prefs.getString("url", "https://teachable-voice-backend-52478641978.asia-south1.run.app"))
        }.also { col.addView(it) }
        keyField = EditText(this).apply {
            hint = "API key (optional)"
            setText(prefs.getString("key", ""))
        }.also { col.addView(it) }
        button("Test connection") { testConnection() }
        button("Enable accessibility service") {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        cmdField = EditText(this).apply {
            hint = "Command, e.g. Order 2 Margherita Pizza from Dominos on Zomato"
        }.also { col.addView(it) }
        button("🎤  Speak command") { listen(null) }
        button("🎤  Speak & RUN") { listen { replay(it) } }
        button("Teach this command") { teach(cmdField.text.toString()) }
        button("Run this command") { replay(cmdField.text.toString()) }
        button("Debug: log screen tree in 5 s") { dumpLater() }
        status = TextView(this).apply { setPadding(0, pad, 0, 0); textSize = 15f }
            .also { col.addView(it) }

        setContentView(ScrollView(this).apply { addView(col) })
    }

    override fun onResume() {
        super.onResume()
        setStatus(if (VoiceFlowService.instance == null)
            "⚠️ Accessibility service is OFF. Tap 'Enable accessibility service' → VoiceFlow → On."
        else "✅ Accessibility service is running.")
    }

    override fun onDestroy() {
        scope.cancel(); super.onDestroy()
    }

    private fun setStatus(s: String) { status.text = s }

    private fun cloud(): CloudClient {
        prefs.edit().putString("url", urlField.text.toString().trim())
            .putString("key", keyField.text.toString().trim()).apply()
        return CloudClient(urlField.text.toString(), keyField.text.toString())
    }

    private fun service(): VoiceFlowService? = VoiceFlowService.instance.also {
        if (it == null) Toast.makeText(this, "Enable the VoiceFlow accessibility service first",
            Toast.LENGTH_LONG).show()
    }

    private fun testConnection() = scope.launch {
        setStatus("Connecting…")
        setStatus(try { "✅ ${cloud().health()}" } catch (e: Exception) { "⚠️ ${e.message}" })
    }

    // ---------------------------------------------------------------- voice --
    private fun listen(then: ((String) -> Unit)?) {
        pendingAfterSpeech = then
        val i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-IN")
            .putExtra(RecognizerIntent.EXTRA_PROMPT, "Say a command")
        try {
            @Suppress("DEPRECATION")
            startActivityForResult(i, REQ_SPEECH)
        } catch (e: Exception) {
            Toast.makeText(this, "No speech recogniser installed; type the command", Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_SPEECH || resultCode != RESULT_OK) return
        val heard = data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull() ?: return
        cmdField.setText(heard)
        pendingAfterSpeech?.invoke(heard)
        pendingAfterSpeech = null
    }

    // ---------------------------------------------------------------- teach --
    private fun teach(command: String) {
        if (command.isBlank()) { setStatus("Say or type the command first."); return }
        val svc = service() ?: return
        svc.startTeaching(command.trim(), cloud())
        setStatus("Teaching \"$command\". Open the app and do the task; tap Done on the floating bar.")
        startActivity(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    // --------------------------------------------------------------- replay --
    private fun replay(command: String, flowId: String? = null, answers: Map<String, Any?> = emptyMap()) {
        if (command.isBlank()) { setStatus("Say or type the command first."); return }
        val svc = service() ?: return
        val client = cloud()
        scope.launch {
            setStatus("Thinking…")
            val r = try {
                client.replay(ReplayRequest(command.trim(), svc.currentPackage, flowId, answers))
            } catch (e: Exception) {
                setStatus("⚠️ Cloud error: ${e.message}"); return@launch
            }
            setStatus(r.message)
            when {
                r.status == "PLAN" -> svc.startReplay(r, client)
                r.status == "ASK_USER" && r.options.isNotEmpty() ->
                    AlertDialog.Builder(this@MainActivity).setTitle(r.question)
                        .setItems(r.options.map { it.label }.toTypedArray()) { _, i ->
                            replay(command, r.options[i].flowId, answers)
                        }.setNegativeButton("Cancel", null).show()
                r.status == "ASK_USER" && r.missingSlot != null -> {
                    val input = EditText(this@MainActivity)
                    AlertDialog.Builder(this@MainActivity).setTitle(r.question).setView(input)
                        .setPositiveButton("OK") { _, _ ->
                            replay(command, r.flowId, answers + (r.missingSlot!! to input.text.toString()))
                        }.setNegativeButton("Cancel", null).show()
                }
                r.status == "NOT_LEARNED" ->
                    AlertDialog.Builder(this@MainActivity).setTitle("Not learned yet")
                        .setMessage(r.message + "\n\nTeach it now?")
                        .setPositiveButton("Teach") { _, _ -> teach(command) }
                        .setNegativeButton("Cancel", null).show()
            }
        }
    }

    private fun dumpLater() {
        val svc = service() ?: return
        setStatus("Switch to the app now — dumping its UI tree to logcat (tag VoiceFlow-Tree) in 5 s.")
        scope.launch {
            delay(5000)
            val tree = svc.dumpScreen()
            setStatus("Dumped ${tree.lines().size} lines to logcat.")
        }
        moveTaskToBack(true)
    }

    companion object { private const val REQ_SPEECH = 42 }
}
