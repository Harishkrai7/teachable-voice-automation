package com.samsung.prism.automation

import android.graphics.Rect
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Utility to read and extract the UI tree from AccessibilityNodeInfo.
 */
object UiTreeReader {
    private const val TAG = "UiTreeReader"

    /**
     * Extracts a semantic UiNode tree from the given AccessibilityNodeInfo.
     * Safely handles nulls and stale nodes.
     */
    fun readTree(nodeInfo: AccessibilityNodeInfo?): UiNode? {
        if (nodeInfo == null) return null

        try {
            // Refresh to ensure node is not stale
            if (!nodeInfo.refresh()) {
                Log.w(TAG, "Failed to refresh AccessibilityNodeInfo, node might be stale")
            }

            val text = nodeInfo.text?.toString()
            val contentDescription = nodeInfo.contentDescription?.toString()
            val resourceId = nodeInfo.viewIdResourceName
            val className = nodeInfo.className?.toString()
            val packageName = nodeInfo.packageName?.toString()
            val clickable = nodeInfo.isClickable
            val enabled = nodeInfo.isEnabled
            
            val bounds = Rect()
            nodeInfo.getBoundsInScreen(bounds)

            val children = mutableListOf<UiNode>()
            for (i in 0 until nodeInfo.childCount) {
                val childNodeInfo = nodeInfo.getChild(i)
                if (childNodeInfo != null) {
                    val childUiNode = readTree(childNodeInfo)
                    if (childUiNode != null) {
                        children.add(childUiNode)
                    }
                    // recycle child node after reading to prevent memory leaks
                    childNodeInfo.recycle()
                }
            }

            return UiNode(
                text = text,
                contentDescription = contentDescription,
                resourceId = resourceId,
                className = className,
                packageName = packageName,
                clickable = clickable,
                enabled = enabled,
                bounds = bounds,
                children = children
            )
        } catch (e: IllegalStateException) {
            Log.e(TAG, "Error reading AccessibilityNodeInfo (likely stale)", e)
            return null
        } catch (e: Exception) {
            Log.e(TAG, "Unexpected error reading UI tree", e)
            return null
        }
    }

    /**
     * Debugging function to log the tree representation.
     */
    fun logTree(node: UiNode, depth: Int = 0) {
        val indent = "  ".repeat(depth)
        Log.d(TAG, "$indent-> $node")
        for (child in node.children) {
            logTree(child, depth + 1)
        }
    }
}
