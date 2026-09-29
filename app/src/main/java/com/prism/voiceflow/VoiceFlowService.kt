package com.prism.voiceflow

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/** Android engine entry point: eyes (events + UI tree) and hands (actions). */
class VoiceFlowService : AccessibilityService() {

    companion object {
        const val TAG = "VoiceFlow"
        @Volatile var instance: VoiceFlowService? = null
            private set
    }

    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    val recorder = Recorder()
    lateinit var overlay: Overlay
        private set
    lateinit var executor: ActionExecutor
        private set
    @Volatile var lastEventAt = 0L
        private set
    var currentPackage: String? = null
        private set
    private var replayJob: Job? = null
    private val ignored = mutableSetOf<String>()

    override fun onServiceConnected() {
        instance = this
        overlay = Overlay(this)
        executor = ActionExecutor(this)
        ignored += packageName
        ignored += "com.android.systemui"
        // Home launchers: tapping the app icon while teaching is not part of the flow.
        val home = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        packageManager.queryIntentActivities(home, PackageManager.MATCH_ALL)
            .forEach { ignored += it.activityInfo.packageName }
        Log.i(TAG, "Service connected; ignoring $ignored")
    }

    override fun onAccessibilityEvent(e: AccessibilityEvent) {
        lastEventAt = SystemClock.uptimeMillis()
        val pkg = e.packageName?.toString() ?: return
        if (pkg in ignored) return

        if (e.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            if (pkg != currentPackage) Log.i(TAG, "Foreground app: $pkg")
            currentPackage = pkg
        }
        if (!recorder.active) return
        val app = recorder.app
        if (app != null && pkg != app) return // keyboards, other apps

        when (e.eventType) {
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                val reason = SafetyGate.sensitiveScreen(rootInActiveWindow)
                if (reason != null && !recorder.blocked) {
                    recorder.blocked = true
                    overlay.show("🔒 Sensitive screen ($reason) — not recording. Tap Done.", "Done") {
                        finishTeaching()
                    }
                }
            }
            AccessibilityEvent.TYPE_VIEW_CLICKED -> e.source?.let {
                recorder.onClick(it)
                if (!recorder.blocked) showTeaching()
            }
            AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> {
                val src = e.source ?: return
                if (e.isPassword || src.isPassword) return
                recorder.onTextChanged(src, e.text.joinToString(""))
                if (!recorder.blocked) showTeaching()
            }
        }
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        cleanup(); return super.onUnbind(intent)
    }

    override fun onDestroy() {
        cleanup(); super.onDestroy()
    }

    private fun cleanup() {
        instance = null
        if (::overlay.isInitialized) overlay.hide()
        scope.cancel()
    }

    // ------------------------------------------------------------- teaching --
    private var teachCloud: CloudClient? = null

    fun startTeaching(command: String, cloud: CloudClient) {
        cancelReplay()
        teachCloud = cloud
        recorder.start(command)
        showTeaching()
    }

    private fun showTeaching() {
        overlay.show("● Teaching: ${recorder.actions.size} actions", "Done") { finishTeaching() }
    }

    fun finishTeaching() {
        val req = recorder.stop()
        val cloud = teachCloud
        if (req == null || cloud == null) {
            overlay.show("Nothing recorded. Open the app and tap through the task.", "OK") { overlay.hide() }
            return
        }
        overlay.show("Learning ${req.actions.size} actions…", null)
        scope.launch {
            val msg = try {
                val r = cloud.teach(req)
                (listOf(if (r.status == "LEARNED") "✅ ${r.message}" else "⚠️ ${r.message}") + r.warnings)
                    .joinToString("\n")
            } catch (e: Exception) {
                Log.e(TAG, "teach failed", e); "⚠️ Cloud error: ${e.message}"
            }
            Log.i(TAG, msg)
            overlay.show(msg, "OK") { overlay.hide() }
        }
    }

    // --------------------------------------------------------------- replay --
    fun startReplay(plan: ReplayResponse, cloud: CloudClient) {
        cancelReplay()
        replayJob = scope.launch {
            val msg = try {
                ReplayEngine(this@VoiceFlowService, cloud).run(plan)
            } catch (e: kotlinx.coroutines.CancellationException) {
                "Stopped."
            } catch (e: Exception) {
                Log.e(TAG, "replay crashed", e); "⚠️ Error: ${e.message}"
            }
            Log.i(TAG, "Replay finished: $msg")
            overlay.show(msg, "OK") { overlay.hide() }
        }
    }

    fun cancelReplay() {
        replayJob?.cancel()
        replayJob = null
    }

    fun dumpScreen(): String = UiTree.dump(rootInActiveWindow).also { tree ->
        tree.chunked(3500).forEach { Log.i("$TAG-Tree", it) }
    }
}

/** Small floating bar drawn over other apps (no extra permission for accessibility services). */
class Overlay(private val svc: AccessibilityService) {
    private val wm = svc.getSystemService(WindowManager::class.java)
    private val handler = Handler(Looper.getMainLooper())
    private var view: LinearLayout? = null
    private lateinit var label: TextView
    private lateinit var button: Button

    private fun ensure() {
        if (view != null) return
        val dp = svc.resources.displayMetrics.density
        label = TextView(svc).apply {
            setTextColor(Color.WHITE); textSize = 14f; maxWidth = (260 * dp).toInt()
        }
        button = Button(svc).apply { textSize = 13f }
        val bar = LinearLayout(svc).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding((14 * dp).toInt(), (6 * dp).toInt(), (6 * dp).toInt(), (6 * dp).toInt())
            background = GradientDrawable().apply {
                setColor(Color.argb(230, 20, 20, 28)); cornerRadius = 18 * dp
            }
            addView(label)
            addView(button)
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            y = (140 * dp).toInt()
        }
        wm.addView(bar, params)
        view = bar
    }

    fun show(message: String, buttonText: String?, onClick: (() -> Unit)? = null) {
        handler.post {
            ensure()
            label.text = message
            if (buttonText == null) {
                button.visibility = View.GONE
            } else {
                button.visibility = View.VISIBLE
                button.text = buttonText
                button.setOnClickListener { onClick?.invoke() }
            }
        }
    }

    fun hide() {
        handler.post {
            view?.let { runCatching { wm.removeView(it) } }
            view = null
        }
    }
}
