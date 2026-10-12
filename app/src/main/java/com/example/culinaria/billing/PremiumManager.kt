package com.example.culinaria.billing

import android.app.Activity
import android.content.Context
import android.widget.Toast
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams

/**
 * Assinatura "Culinária Premium" via Google Play Billing.
 *
 * Configure no Play Console: Monetizar > Produtos > Assinaturas, com o ID [PRODUCT_ID]
 * e ao menos um plano base (por exemplo mensal e anual).
 */
object PremiumManager : PurchasesUpdatedListener {

    /** ID da assinatura cadastrada no Play Console. */
    const val PRODUCT_ID = "culinaria_premium"

    private const val PREFS = "premium"
    private const val KEY_PREMIUM = "is_premium"

    private val premiumState = MutableLiveData(false)
    val isPremium: LiveData<Boolean> = premiumState

    /** Preço formatado (ex.: "R$ 9,90") quando disponível; null se ainda não carregou. */
    @Volatile
    var priceText: String? = null
        private set

    private var appContext: Context? = null
    private var client: BillingClient? = null
    private var productDetails: ProductDetails? = null

    fun isPremiumNow(): Boolean = premiumState.value == true

    fun init(context: Context) {
        if (client != null) return
        val app = context.applicationContext
        appContext = app
        // Mostra o último estado conhecido enquanto a Play Store responde (uso offline).
        premiumState.value = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_PREMIUM, false)

        client = BillingClient.newBuilder(app)
            .setListener(this)
            .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
            .enableAutoServiceReconnection()
            .build()
        connect()
    }

    private fun connect() {
        client?.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    queryPurchases()
                    queryProduct()
                }
            }

            override fun onBillingServiceDisconnected() = Unit
        })
    }

    /** Reconsulta compras e produto (use ao voltar para o app). */
    fun refresh() {
        if (client?.isReady == true) {
            queryPurchases()
            queryProduct()
        } else {
            connect()
        }
    }

    private fun queryPurchases() {
        val params = QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.SUBS)
            .build()
        client?.queryPurchasesAsync(params) { result, purchases ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) handlePurchases(purchases)
        }
    }

    private fun queryProduct() {
        val product = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(PRODUCT_ID)
            .setProductType(BillingClient.ProductType.SUBS)
            .build()
        val params = QueryProductDetailsParams.newBuilder().setProductList(listOf(product)).build()
        client?.queryProductDetailsAsync(params) { result, queryResult ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                productDetails = queryResult.productDetailsList.firstOrNull()
                priceText = productDetails?.subscriptionOfferDetails
                    ?.firstOrNull()
                    ?.pricingPhases?.pricingPhaseList
                    ?.lastOrNull()
                    ?.formattedPrice
            }
        }
    }

    /** Abre a tela de compra do Google Play. */
    fun launchPurchase(activity: Activity) {
        val details = productDetails
        val offerToken = details?.subscriptionOfferDetails?.firstOrNull()?.offerToken
        if (client?.isReady != true || details == null || offerToken == null) {
            Toast.makeText(
                activity,
                "Assinatura indisponível no momento. Verifique sua conexão e tente novamente.",
                Toast.LENGTH_LONG
            ).show()
            refresh()
            return
        }
        val productParams = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(details)
            .setOfferToken(offerToken)
            .build()
        val flowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(productParams))
            .build()
        client?.launchBillingFlow(activity, flowParams)
    }

    override fun onPurchasesUpdated(result: BillingResult, purchases: MutableList<Purchase>?) {
        if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            handlePurchases(purchases)
        }
    }

    private fun handlePurchases(purchases: List<Purchase>) {
        val active = purchases.filter {
            it.products.contains(PRODUCT_ID) && it.purchaseState == Purchase.PurchaseState.PURCHASED
        }
        // A Play cancela o reembolso automático se a compra não for reconhecida em 3 dias.
        active.filter { !it.isAcknowledged }.forEach { purchase ->
            val ack = AcknowledgePurchaseParams.newBuilder().setPurchaseToken(purchase.purchaseToken).build()
            client?.acknowledgePurchase(ack) { }
        }
        setPremium(active.isNotEmpty())
    }

    private fun setPremium(value: Boolean) {
        appContext?.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            ?.edit()?.putBoolean(KEY_PREMIUM, value)?.apply()
        premiumState.postValue(value)
    }
}
