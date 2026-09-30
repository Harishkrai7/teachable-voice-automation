package com.samsung.prism.automation

import android.view.accessibility.AccessibilityNodeInfo
import java.util.Locale

object NodeMatcher {

    enum class MatchConfidence {
        HIGH, MODERATE, LOW, NONE
    }

    data class MatchResult(
        val node: AccessibilityNodeInfo,
        val confidence: MatchConfidence
    )

    fun findBestMatch(
        root: AccessibilityNodeInfo?,
        target: String,
        actionType: String
    ): AccessibilityNodeInfo? {
        if (root == null || target.isBlank()) return null
        
        val candidates = mutableListOf<MatchResult>()
        searchNodes(root, target, actionType, candidates)

        // Filter and sort candidates
        val safeCandidates = candidates.filter { it.confidence != MatchConfidence.NONE && it.confidence != MatchConfidence.LOW }
        if (safeCandidates.isEmpty()) return null
        
        val bestMatches = safeCandidates.sortedByDescending { 
            when (it.confidence) {
                MatchConfidence.HIGH -> 3
                MatchConfidence.MODERATE -> 2
                else -> 1
            }
        }
        
        // Check ambiguity
        if (bestMatches.size > 1 && bestMatches[0].confidence == bestMatches[1].confidence) {
            // Ambiguous node match. We refuse to randomly pick.
            return null
        }
        
        return bestMatches.firstOrNull()?.node
    }

    private fun searchNodes(
        node: AccessibilityNodeInfo,
        target: String,
        actionType: String,
        candidates: MutableList<MatchResult>
    ) {
        if (!node.refresh()) return
        
        // Basic safety rejections
        if (!node.isVisibleToUser || !node.isEnabled) {
            // Recurse children anyway, maybe a child is visible
        } else {
            val score = evaluateNode(node, target, actionType)
            if (score != MatchConfidence.NONE) {
                candidates.add(MatchResult(node, score))
            }
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child != null) {
                searchNodes(child, target, actionType, candidates)
                // Don't recycle child here because it might be added to candidates
            }
        }
    }

    private fun evaluateNode(
        node: AccessibilityNodeInfo,
        target: String,
        actionType: String
    ): MatchConfidence {
        val text = node.text?.toString() ?: ""
        val desc = node.contentDescription?.toString() ?: ""
        val resId = node.viewIdResourceName ?: ""
        val className = node.className?.toString() ?: ""
        
        val normTarget = normalize(target)
        val normText = normalize(text)
        val normDesc = normalize(desc)
        
        // Exact text match
        if (normText == normTarget || normDesc == normTarget) {
            if (isActionCompatible(node, actionType)) return MatchConfidence.HIGH
            return MatchConfidence.MODERATE
        }
        
        // Substring / Normalized text match
        if ((normText.isNotEmpty() && normText.contains(normTarget)) || 
            (normDesc.isNotEmpty() && normDesc.contains(normTarget))) {
            if (isActionCompatible(node, actionType)) return MatchConfidence.MODERATE
            return MatchConfidence.LOW
        }
        
        // Resource ID match (fallback for items without text like search fields)
        if (resId.lowercase(Locale.getDefault()).contains(normTarget)) {
            if (isActionCompatible(node, actionType)) return MatchConfidence.MODERATE
        }
        
        return MatchConfidence.NONE
    }

    private fun isActionCompatible(node: AccessibilityNodeInfo, actionType: String): Boolean {
        return when (actionType) {
            "SEARCH", "TYPE_TEXT" -> node.isEditable
            "SELECT", "CLICK", "ADD_TO_CART" -> node.isClickable
            "SCROLL" -> node.isScrollable
            "SET_QUANTITY" -> node.isEditable || node.isClickable
            else -> false
        }
    }

    private fun normalize(input: String): String {
        return input.trim().lowercase(Locale.getDefault()).replace(Regex("\\s+"), " ")
    }
}
