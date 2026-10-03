package com.prism.voiceflow

import android.view.accessibility.AccessibilityNodeInfo

/** Same normalisation/similarity rules as backend/app/textutil.py. */
object TextUtil {
    private val nonAlnum = Regex("[^a-z0-9 ]+")

    private fun stem(w: String) =
        if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) w.dropLast(1) else w

    fun norm(s: CharSequence?): String {
        if (s.isNullOrBlank()) return ""
        return nonAlnum.replace(s.toString().lowercase(), " ")
            .split(" ").filter { it.isNotBlank() }.joinToString(" ") { stem(it) }
    }

    fun similarity(a: CharSequence?, b: CharSequence?): Double {
        val na = norm(a)
        val nb = norm(b)
        if (na.isEmpty() || nb.isEmpty()) return 0.0
        if (na == nb) return 1.0
        val shorter = if (na.length <= nb.length) na else nb
        val longer = if (na.length <= nb.length) nb else na
        if (shorter.length >= 3 && " $longer ".contains(" $shorter ")) return 0.9
        val ta = na.split(" ").toSet()
        val tb = nb.split(" ").toSet()
        val overlap = ta.intersect(tb).size.toDouble() / maxOf(ta.size, tb.size)
        return maxOf(levRatio(na, nb), overlap * 0.85)
    }

    private fun levRatio(a: String, b: String): Double {
        if (a.length > 80 || b.length > 80) return 0.0
        val prev = IntArray(b.length + 1) { it }
        val cur = IntArray(b.length + 1)
        for (i in 1..a.length) {
            cur[0] = i
            for (j in 1..b.length) {
                val cost = if (a[i - 1] == b[j - 1]) 0 else 1
                cur[j] = minOf(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            }
            System.arraycopy(cur, 0, prev, 0, cur.size)
        }
        return 1.0 - prev[b.length].toDouble() / maxOf(a.length, b.length)
    }
}

/** Hard safety boundary. Automation never taps these and stops on these screens. */
object SafetyGate {
    private val screenPatterns = listOf(
        """\botp\b""", """\bone[- ]time password\b""", """\bverification code\b""",
        """\bpassword\b""", """\bpin\b(?! ?code)""", """\bcvv\b""", """\bcard number\b""",
        """\bupi pin\b""", """\blog ?in\b""", """\bsign ?in\b""",
    )
    private val actionPatterns = listOf(
        """\bpay(ment)?\b""", """\bproceed to pay\b""", """\bplace (your )?order\b""",
        """\bbuy now\b""", """\bconfirm order\b""",
    ) + screenPatterns
    private val actionRe = Regex(actionPatterns.joinToString("|"), RegexOption.IGNORE_CASE)
    private val screenRe = Regex(screenPatterns.joinToString("|"), RegexOption.IGNORE_CASE)
    private val enterRe = Regex("""\benter (the )?(otp|pin|password|upi pin|cvv)\b""", RegexOption.IGNORE_CASE)

    private fun idWords(id: String?) =
        id?.substringAfterLast('/')?.replace(Regex("[_/:.]+"), " ") ?: ""

    /** Is tapping this node a payment/auth action? Returns the reason or null. */
    fun sensitiveNode(n: AccessibilityNodeInfo): String? {
        if (n.isPassword) return "password field"
        val fields = listOf(n.text?.toString() ?: "", n.contentDescription?.toString() ?: "",
            idWords(n.viewIdResourceName), UiTree.deepLabel(n) ?: "")
        for (f in fields) actionRe.find(f)?.let { return it.value }
        return null
    }

    /** Is the current screen a login/OTP/PIN/payment-entry screen? */
    fun sensitiveScreen(root: AccessibilityNodeInfo?): String? {
        if (root == null) return null
        for (n in UiTree.visible(root)) {
            if (n.isPassword) return "password field"
            if (n.isEditable) {
                val fields = listOf(n.text?.toString() ?: "", n.hintText?.toString() ?: "",
                    n.contentDescription?.toString() ?: "", idWords(n.viewIdResourceName))
                for (f in fields) screenRe.find(f)?.let { return it.value }
            }
            n.text?.let { t -> enterRe.find(t)?.let { return it.value } }
        }
        return null
    }
}
