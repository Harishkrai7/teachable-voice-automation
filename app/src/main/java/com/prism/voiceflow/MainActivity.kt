package com.prism.voiceflow

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognizerIntent
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class MainActivity : Activity() {

    private val scope = MainScope()

    private lateinit var etCommand: EditText
    private lateinit var tvStatus: TextView
    private var pendingAfterSpeech: ((String) -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etCommand   = findViewById(R.id.etCommand)
        tvStatus    = findViewById(R.id.tvStatus)

        // Accessibility shortcut button
        findViewById<Button>(R.id.btnEnableA11y).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }

        // Voice buttons
        findViewById<Button>(R.id.btnSpeak).setOnClickListener { listen(null) }
        findViewById<Button>(R.id.btnSpeakRun).setOnClickListener { listen { replay(it) } }

        // Teach / Run
        findViewById<Button>(R.id.btnTeach).setOnClickListener {
            teach(etCommand.text.toString())
        }
        findViewById<Button>(R.id.btnRun).setOnClickListener {
            replay(etCommand.text.toString())
        }

        // Debug
        findViewById<Button>(R.id.btnDebug).setOnClickListener { dumpLater() }
    }

    override fun onResume() {
        super.onResume()
        val svcRunning = VoiceFlowService.instance != null
        tvStatus.text = if (svcRunning)
            "✅ Accessibility service is running."
        else
            "⚠️ Accessibility service is OFF — tap ⚙ to enable."
        // Colour the dot
        val dot = findViewById<View>(R.id.tvStatusDot)
        dot.background = if (svcRunning)
            resources.getDrawable(R.drawable.bg_dot_green, theme)
        else
            resources.getDrawable(R.drawable.bg_dot_red, theme)
    }

    override fun onDestroy() {
        scope.cancel(); super.onDestroy()
    }

    // ---------------------------------------------------------------- cloud --
    private fun cloud(): CloudClient {
        return CloudClient(BuildConfig.BASE_URL, null)
    }

    private fun service(): VoiceFlowService? = VoiceFlowService.instance.also {
        if (it == null) Toast.makeText(this,
            "Enable the VoiceFlow accessibility service first", Toast.LENGTH_LONG).show()
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
            Toast.makeText(this, "No speech recogniser installed; type the command",
                Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_SPEECH || resultCode != RESULT_OK) return
        val heard = data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull() ?: return
        etCommand.setText(heard)
        pendingAfterSpeech?.invoke(heard)
        pendingAfterSpeech = null
    }

    // ---------------------------------------------------------------- teach --
    private fun teach(command: String) {
        if (command.isBlank()) {
            Toast.makeText(this, "Say or type the command first.", Toast.LENGTH_SHORT).show()
            return
        }
        val svc = service() ?: return
        val client = try { cloud() } catch (e: Exception) { return }
        svc.startTeaching(command.trim(), client)
        tvStatus.text = "Teaching \"$command\" — open the target app and perform the task, then tap Done on the bar."
        startActivity(Intent(Intent.ACTION_MAIN)
            .addCategory(Intent.CATEGORY_HOME)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    // --------------------------------------------------------------- replay --
    private fun replay(command: String, flowId: String? = null, answers: Map<String, Any?> = emptyMap()) {
        if (command.isBlank()) {
            Toast.makeText(this, "Say or type the command first.", Toast.LENGTH_SHORT).show()
            return
        }
        val svc = service() ?: return
        val client = try { cloud() } catch (e: Exception) { return }
        scope.launch {
            tvStatus.text = "Thinking…"
            val r = try {
                client.replay(ReplayRequest(command.trim(), svc.currentPackage, flowId, answers))
            } catch (e: Exception) {
                tvStatus.text = "⚠️ Cloud error: ${e.message}"; return@launch
            }
            tvStatus.text = r.message
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
        tvStatus.text = "Switch to the app now — dumping its UI tree to logcat in 5 s."
        scope.launch {
            kotlinx.coroutines.delay(5000)
            val tree = svc.dumpScreen()
            tvStatus.text = "Dumped ${tree.lines().size} lines to logcat (tag VoiceFlow-Tree)."
        }
        moveTaskToBack(true)
    }

    companion object { private const val REQ_SPEECH = 42 }
}
