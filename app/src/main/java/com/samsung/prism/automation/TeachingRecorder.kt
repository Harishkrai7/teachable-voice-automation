package com.samsung.prism.automation

import android.util.Log

object TeachingRecorder {
    private const val TAG = "TeachingRecorder"
    
    private val recordedActions = mutableListOf<TeachingAction>()
    private var isRecording = true // Set to true by default to capture immediately for Person 1 tests

    // To prevent duplicate clicks/events
    private var lastRecordedActionType: ActionType? = null
    private var lastRecordedTimestamp: Long = 0
    private const val DEBOUNCE_MS = 500L

    fun startRecording() {
        isRecording = true
        recordedActions.clear()
        Log.e(TAG, "========== RECORDING STARTED ==========")
    }

    fun stopRecording() {
        isRecording = false
        Log.e(TAG, "========== RECORDING STOPPED ==========")
    }

    fun clear() {
        recordedActions.clear()
        Log.e(TAG, "========== RECORDING CLEARED ==========")
    }

    fun recordAction(action: TeachingAction) {
        if (!isRecording) return

        // Filter duplicates (debounce) based on type and timestamp
        if (action.type == lastRecordedActionType) {
            if (action.timestamp - lastRecordedTimestamp < DEBOUNCE_MS) {
                Log.d(TAG, "Ignoring duplicate/noisy ${action.type} event within debounce window.")
                return
            }
        }

        // Safety check for sensitive information
        if (action.target?.isSensitive == true) {
            Log.e(TAG, "Skipping sensitive target record.")
            return
        }

        recordedActions.add(action)
        lastRecordedActionType = action.type
        lastRecordedTimestamp = action.timestamp

        Log.e(TAG, "========== ACTION RECORDED ==========")
        Log.e(TAG, "Action Type: ${action.type}")
        Log.e(TAG, "Target: ${action.target}")
        Log.e(TAG, "Total Recorded Actions: ${recordedActions.size}")
    }

    fun getActions(): List<TeachingAction> {
        return recordedActions.toList()
    }
}
