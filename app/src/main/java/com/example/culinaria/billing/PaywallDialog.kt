package com.example.culinaria.billing

import android.app.Activity
import android.content.Intent
import android.net.Uri
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment

/** Substitua pela URL pública da sua política de privacidade (obrigatória na Play Store). */
const val PRIVACY_POLICY_URL = "https://fiscon421811.github.io/culinaria/privacidade"

/** Decide se uma função de IA pode ser usada e mostra a oferta Premium quando a cota acaba. */
object AiAccess {
    fun ensureAllowed(fragment: Fragment): Boolean {
        val context = fragment.requireContext()
        PremiumManager.init(context)
        if (PremiumManager.isPremiumNow() || AiQuota.remaining(context) > 0) return true
        PaywallDialog.show(fragment.requireActivity(), limitReached = true)
        return false
    }

    fun registerSuccess(context: android.content.Context) {
        if (!PremiumManager.isPremiumNow()) AiQuota.registerUse(context)
    }

    fun statusText(context: android.content.Context): String =
        if (PremiumManager.isPremiumNow()) "Premium ativo: importações com IA ilimitadas."
        else "Restam ${AiQuota.remaining(context)} de ${AiQuota.FREE_DAILY_LIMIT} importações com IA gratuitas hoje."
}

object PaywallDialog {
    fun show(activity: Activity, limitReached: Boolean = false) {
        PremiumManager.init(activity)
        PremiumManager.refresh()

        val builder = AlertDialog.Builder(activity)
            .setTitle("⭐ Culinária Premium")
            .setNeutralButton("PRIVACIDADE") { _, _ -> openUrl(activity, PRIVACY_POLICY_URL) }

        if (PremiumManager.isPremiumNow()) {
            builder
                .setMessage("Você é Premium. Obrigado por apoiar o app!\n\nImportações com IA ilimitadas.")
                .setPositiveButton("GERENCIAR ASSINATURA") { _, _ ->
                    openUrl(
                        activity,
                        "https://play.google.com/store/account/subscriptions?sku=${PremiumManager.PRODUCT_ID}&package=${activity.packageName}"
                    )
                }
                .setNegativeButton("FECHAR", null)
        } else {
            val intro = if (limitReached) {
                "Você usou as ${AiQuota.FREE_DAILY_LIMIT} importações gratuitas com IA de hoje. Elas voltam amanhã.\n\n"
            } else {
                "${AiAccess.statusText(activity)}\n\n"
            }
            val price = PremiumManager.priceText?.let { "\nAssine por $it (renovação automática, cancele quando quiser no Google Play)." }.orEmpty()
            builder
                .setMessage(
                    intro +
                        "Com o Premium você tem:\n" +
                        "• Importar receitas com IA sem limite diário\n" +
                        "• Gerar receitas do cardápio semanal sem limite\n" +
                        "• Apoia o desenvolvimento e os custos da IA" +
                        price
                )
                .setPositiveButton("ASSINAR") { _, _ -> PremiumManager.launchPurchase(activity) }
                .setNegativeButton("AGORA NÃO", null)
        }
        builder.show()
    }

    private fun openUrl(activity: Activity, url: String) {
        runCatching { activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
    }
}
