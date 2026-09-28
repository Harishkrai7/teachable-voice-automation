package com.samsung.prism.automation

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.samsung.prism.automation.api.*
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.net.SocketTimeoutException

class MainActivity : AppCompatActivity() {

    private lateinit var etUtterance: EditText
    private lateinit var btnTeach: Button
    private lateinit var btnReplay: Button
    private lateinit var tvResult: TextView

    private val BASE_URL = BuildConfig.BASE_URL

    private val api: Cloud1Api by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(Cloud1Api::class.java)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etUtterance = findViewById(R.id.etUtterance)
        val btnStartTeach = findViewById<Button>(R.id.btnStartTeach)
        val btnStopTeach = findViewById<Button>(R.id.btnStopTeach)
        val btnClear = findViewById<Button>(R.id.btnClear)
        val btnStartReplay = findViewById<Button>(R.id.btnStartReplay)
        val btnStopReplay = findViewById<Button>(R.id.btnStopReplay)
        btnTeach = findViewById(R.id.btnTeach)
        btnReplay = findViewById(R.id.btnReplay)
        tvResult = findViewById(R.id.tvResult)

        btnStartReplay.setOnClickListener {
            if (lastReplayPlan != null) {
                ReplaySessionManager.startReplay(lastFlowId, lastReplayPlan!!, "com.example.shopping")
                ReplayEngine.start()
                // Simple polling to update debug UI during replay
                CoroutineScope(Dispatchers.Main).launch {
                    while (ReplaySessionManager.getState() != ReplaySessionManager.State.IDLE &&
                           ReplaySessionManager.getState() != ReplaySessionManager.State.STOPPED &&
                           ReplaySessionManager.getState() != ReplaySessionManager.State.COMPLETED &&
                           ReplaySessionManager.getState() != ReplaySessionManager.State.FAILED) {
                        updateDebugUI()
                        delay(500)
                    }
                    updateDebugUI() // Final update

                    if (ReplaySessionManager.getState() == ReplaySessionManager.State.FAILED) {
                        val failedAction = ReplaySessionManager.failedAction
                        if (failedAction != null) {
                            val apiAction = Action(
                                action = failedAction.action,
                                target = failedAction.target,
                                value = failedAction.value
                            )
                            val req = ReplayFailureFeedback(
                                flowId = ReplaySessionManager.getFlowId() ?: "unknown",
                                actionIndex = ReplaySessionManager.getCurrentIndex(),
                                failedAction = apiAction,
                                reason = ReplaySessionManager.lastFailureReason ?: "UNKNOWN",
                                currentApp = ReplaySessionManager.currentApp ?: "unknown"
                            )
                            try {
                                val resp = api.sendFeedback(req)
                                if (resp.isSuccessful) {
                                    val feedbackData = resp.body()
                                    if (feedbackData != null) {
                                        withContext(Dispatchers.Main) {
                                            tvResult.append("\nCloud decision: ${feedbackData.status}")
                                        }
                                    }
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "Feedback submission failed", e)
                            }
                        }
                    }
                }
            } else {
                tvResult.text = "No replay plan available. Please request one first."
            }
        }

        btnStopReplay.setOnClickListener {
            ReplayEngine.stop()
            updateDebugUI()
        }

        btnStartTeach.setOnClickListener {
            TeachSessionManager.startSession()
            updateDebugUI()
        }

        btnClear.setOnClickListener {
            TeachSessionManager.clear()
            updateDebugUI()
        }

        btnStopTeach.setOnClickListener {
            val actions = TeachSessionManager.stopSession()
            val utterance = etUtterance.text.toString().trim()
            if (utterance.isEmpty()) {
                tvResult.text = "Please enter an utterance before stopping teach."
                return@setOnClickListener
            }
            if (actions.isEmpty()) {
                tvResult.text = "No actions recorded."
                return@setOnClickListener
            }

            tvResult.text = "Sending REAL TEACH request..."
            
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val apiActions = actions.map { 
                        Action(action = it.action, target = it.target, value = it.value) 
                    }
                    val request = TeachRequest(
                        utterance = utterance,
                        app = TeachSessionManager.getCurrentPackage() ?: "com.example.shopping",
                        actions = apiActions
                    )
                    
                    val response = api.processTeach(request)
                    handleResponse(response)
                } catch (e: Exception) {
                    handleError(e)
                }
            }
        }

        btnTeach.setOnClickListener {
            val utterance = etUtterance.text.toString().trim()
            if (utterance.isEmpty()) {
                tvResult.text = "Please enter an utterance"
                return@setOnClickListener
            }
            
            tvResult.text = "Sending MOCK TEACH request..."
            
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val request = TeachRequest(
                        utterance = utterance,
                        app = "Zomato",
                        actions = listOf(
                            Action("SEARCH", target = "Dominos"),
                            Action("SELECT", target = "Dominos"),
                            Action("SEARCH", target = "Margherita Pizza"),
                            Action("SET_QUANTITY", value = "1"),
                            Action("ADD_TO_CART"),
                            Action("OPEN_CART")
                        )
                    )
                    
                    val response = api.processTeach(request)
                    handleResponse(response)
                } catch (e: Exception) {
                    handleError(e)
                }
            }
        }

        btnReplay.setOnClickListener {
            val utterance = etUtterance.text.toString().trim()
            if (utterance.isEmpty()) {
                tvResult.text = "Please enter an utterance"
                return@setOnClickListener
            }
            
            tvResult.text = "Sending REPLAY request..."
            
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val request = ReplayRequest(
                        utterance = utterance,
                        currentApp = "Zomato"
                    )
                    
                    val response = api.processReplay(request)
                    handleResponse(response)
                } catch (e: Exception) {
                    handleError(e)
                }
            }
        }
    }
    
    private suspend fun handleResponse(response: retrofit2.Response<ProcessResponse>) {
        withContext(Dispatchers.Main) {
            if (response.isSuccessful) {
                val data = response.body()
                if (data != null) {
                    if (data.type == "ASK_USER") {
                        tvResult.text = "ASK_USER: ${data.question}"
                    } else if (data.type == "STOP") {
                        tvResult.text = "STOP! Reason: ${data.reason}"
                    } else if (data.type == "NOT_LEARNED") {
                        tvResult.text = "NOT_LEARNED: ${data.message}"
                    } else if (data.mode == "TEACH") {
                        val flowStr = data.flow?.let {
                            "FlowId: ${it.flowId}\nIntent: ${it.intent}\nSlots: ${it.slots}\nGeneralized Steps: ${it.steps}"
                        } ?: "Flow data missing"
                        tvResult.text = "TEACH Successful!\n\n$flowStr"
                    } else if (data.mode == "REPLAY") {
                        val plan = data.actions?.map { 
                            ConcreteAction(action = it.action, target = it.target, value = it.value) 
                        }
                        if (plan != null) {
                            lastReplayPlan = plan
                            lastFlowId = data.flowId ?: "unknown"
                            updateDebugUI()
                        } else {
                            tvResult.text = "REPLAY Successful but no actions found."
                        }
                    }
                }
            } else {
                val errorBody = response.errorBody()?.string()
                try {
                    val errorResp = Gson().fromJson(errorBody, ErrorResponse::class.java)
                    tvResult.text = "Error: ${response.code()}\nCode: ${errorResp.error?.code}\nMessage: ${errorResp.error?.message}"
                } catch (e: Exception) {
                    tvResult.text = "HTTP Error: ${response.code()}\n${errorBody}"
                }
            }
        }
    }
    
    private suspend fun handleError(e: Exception) {
        withContext(Dispatchers.Main) {
            if (e is SocketTimeoutException) {
                tvResult.text = "Timeout Error: Could not connect to Cloud."
            } else {
                tvResult.text = "Network Exception: ${e.message}"
            }
        }
    }
    private var lastReplayPlan: List<ConcreteAction>? = null
    private var lastFlowId: String = ""

    private fun updateDebugUI() {
        val isTeaching = TeachSessionManager.isTeaching()
        val actions = TeachSessionManager.getActions()
        
        val sb = StringBuilder()
        sb.append("Teaching: ${if (isTeaching) "ON" else "OFF"}\n")
        sb.append("Current Package: ${TeachSessionManager.getCurrentPackage() ?: "None"}\n\n")
        sb.append("Captured Actions:\n")
        
        actions.forEachIndexed { index, action ->
            sb.append("${index + 1}. ${action.action}")
            if (action.target != null) sb.append(" → target=${action.target}")
            if (action.value != null) sb.append(" → value=${action.value}")
            sb.append("\n")
        }
        
        // Replay Status
        val replayState = ReplaySessionManager.getState()
        sb.append("\nReplay status:\n${replayState}\n")
        if (replayState != ReplaySessionManager.State.IDLE && replayState != ReplaySessionManager.State.STOPPED) {
            sb.append("Flow: ${ReplaySessionManager.getFlowId()}\n")
            val currentAction = ReplaySessionManager.getCurrentAction()
            val total = ReplaySessionManager.getTotalActions()
            val idx = ReplaySessionManager.getCurrentIndex() + 1
            if (currentAction != null) {
                sb.append("Current action: $idx / $total\n")
                sb.append("${currentAction.action} → ${currentAction.target}\n")
            }
            if (replayState == ReplaySessionManager.State.FAILED) {
                sb.append("\nReason: ${ReplaySessionManager.lastFailureReason}\n")
            }
        }
        
        tvResult.text = sb.toString()
    }
}
