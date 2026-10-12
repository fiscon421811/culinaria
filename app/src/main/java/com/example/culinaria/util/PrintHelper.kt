package com.example.culinaria.util


import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.pdf.PdfDocument
import android.widget.Toast
import androidx.core.content.FileProvider
import com.example.culinaria.model.Receita
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object PrintHelper {

    private const val PAGE_W = 595
    private const val PAGE_H = 842
    private const val MARGIN = 40f

    private val COR_PRIMARIA = Color.parseColor("#E65100")
    private val COR_TEXTO = Color.parseColor("#212121")
    private val COR_SECUNDARIO = Color.parseColor("#757575")

    fun imprimirReceita(context: Context, receita: Receita) {
        try {
            val arquivo = gerarPdfReceita(context, receita)
            abrirPdf(context, arquivo)
        } catch (e: Exception) {
            Toast.makeText(context, "Erro ao gerar PDF: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    fun imprimirLista(context: Context, receitas: List<Receita>, titulo: String = "Livro de Receitas") {
        try {
            val arquivo = gerarPdfLista(context, receitas, titulo)
            abrirPdf(context, arquivo)
        } catch (e: Exception) {
            Toast.makeText(context, "Erro ao gerar PDF: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun gerarPdfReceita(context: Context, receita: Receita): File {
        val doc = PdfDocument()
        var pageNum = 1
        var pageInfo = PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNum).create()
        var page = doc.startPage(pageInfo)
        var canvas = page.canvas
        var y = MARGIN

        y = desenharCabecalho(canvas, "Livro de Receitas", "Receita Nº ${receita.cod.toString().padStart(3, '0')}", y)
        y += 20f

        val pTitulo = paintTexto(18f, COR_PRIMARIA, bold = true)
        y = drawTextWrapped(canvas, receita.titulo, MARGIN, y, PAGE_W - MARGIN * 2, pTitulo)
        y += 6f

        val pLinha = Paint().apply { color = COR_PRIMARIA; strokeWidth = 1.5f }
        canvas.drawLine(MARGIN, y, PAGE_W - MARGIN, y, pLinha)
        y += 12f

        y = desenharBadge(canvas, "Cód. ${receita.cod}", MARGIN, y)
        y = desenharBadge(canvas, "Categoria ${receita.codCat}", MARGIN + 110f, y - 22f)
        y += 16f

        val pCorpo = paintTexto(12f, COR_TEXTO)
        val linhas = quebrarLinhas(receita.receita, PAGE_W - MARGIN * 2, pCorpo)

        for (linha in linhas) {
            if (y + 16f > PAGE_H - MARGIN) {
                doc.finishPage(page)
                pageNum++
                pageInfo = PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNum).create()
                page = doc.startPage(pageInfo)
                canvas = page.canvas
                y = MARGIN
                desenharRodape(canvas, pageNum)
            }
            canvas.drawText(linha, MARGIN, y, pCorpo)
            y += 18f
        }

        if (!receita.link.isNullOrBlank()) {
            y += 12f
            val pLink = paintTexto(10f, Color.parseColor("#1565C0"))
            y = drawTextWrapped(canvas, "🔗 ${receita.link}", MARGIN, y, PAGE_W - MARGIN * 2, pLink)
        }

        desenharRodape(canvas, pageNum)
        doc.finishPage(page)

        return salvarPdf(context, doc, "Receita_${receita.cod}")
    }

    private fun gerarPdfLista(context: Context, receitas: List<Receita>, titulo: String): File {
        val doc = PdfDocument()
        var pageNum = 1
        var pageInfo = PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNum).create()
        var page = doc.startPage(pageInfo)
        var canvas = page.canvas
        var y = MARGIN

        y = desenharCabecalho(canvas, titulo, "${receitas.size} receita(s) — ${dataAtual()}", y)
        y += 20f

        val pNum = paintTexto(13f, COR_PRIMARIA, bold = true)
        val pNome = paintTexto(13f, COR_TEXTO, bold = true)
        val pCorpo = paintTexto(11f, COR_TEXTO)
        val pLink = paintTexto(9f, Color.parseColor("#1565C0"))
        val pCat = paintTexto(9f, COR_SECUNDARIO)

        for (receita in receitas) {
            if (y + 50f > PAGE_H - MARGIN) {
                desenharRodape(canvas, pageNum)
                doc.finishPage(page)
                pageNum++
                pageInfo = PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNum).create()
                page = doc.startPage(pageInfo)
                canvas = page.canvas
                y = MARGIN
            }

            val pFaixa = Paint().apply { color = Color.parseColor("#FFF3E0") }
            canvas.drawRoundRect(RectF(MARGIN, y, PAGE_W - MARGIN, y + 28f), 6f, 6f, pFaixa)
            val pBorda = Paint().apply {
                color = COR_PRIMARIA; style = Paint.Style.STROKE; strokeWidth = 3f
            }
            canvas.drawRoundRect(RectF(MARGIN, y, PAGE_W - MARGIN, y + 28f), 6f, 6f, pBorda)

            canvas.drawText(receita.cod.toString().padStart(3, '0'), MARGIN + 8f, y + 19f, pNum)
            canvas.drawText(receita.titulo, MARGIN + 52f, y + 19f, pNome)
            canvas.drawText("Cat.${receita.codCat}", PAGE_W - MARGIN - 50f, y + 19f, pCat)
            y += 34f

            val linhas = quebrarLinhas(receita.receita, PAGE_W - MARGIN * 2, pCorpo)
            for (linha in linhas) {
                if (y + 14f > PAGE_H - MARGIN) {
                    desenharRodape(canvas, pageNum)
                    doc.finishPage(page)
                    pageNum++
                    pageInfo = PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNum).create()
                    page = doc.startPage(pageInfo)
                    canvas = page.canvas
                    y = MARGIN
                }
                canvas.drawText(linha, MARGIN, y, pCorpo)
                y += 15f
            }

            if (!receita.link.isNullOrBlank()) {
                y += 4f
                canvas.drawText("🔗 ${receita.link}", MARGIN, y, pLink)
                y += 14f
            }

            y += 6f
            val pDiv = Paint().apply { color = Color.parseColor("#E0E0E0"); strokeWidth = 1f }
            canvas.drawLine(MARGIN, y, PAGE_W - MARGIN, y, pDiv)
            y += 12f
        }

        desenharRodape(canvas, pageNum)
        doc.finishPage(page)

        return salvarPdf(context, doc, titulo.replace(" ", "_"))
    }

    private fun desenharCabecalho(canvas: Canvas, titulo: String, subtitulo: String, y: Float): Float {
        val altCab = 70f
        val pFundo = Paint().apply { color = COR_PRIMARIA }
        canvas.drawRect(0f, 0f, PAGE_W.toFloat(), altCab, pFundo)

        val pTitulo = paintTexto(20f, Color.WHITE, bold = true)
        canvas.drawText(titulo, MARGIN, 36f, pTitulo)

        val pSub = paintTexto(11f, Color.parseColor("#FFCC80"))
        canvas.drawText(subtitulo, MARGIN, 55f, pSub)

        return altCab + 10f
    }

    private fun desenharBadge(canvas: Canvas, texto: String, x: Float, y: Float): Float {
        val pFundo = Paint().apply { color = Color.parseColor("#FFF3E0") }
        val pBorda = Paint().apply {
            color = COR_PRIMARIA; style = Paint.Style.STROKE; strokeWidth = 1f
        }
        val pTexto = paintTexto(9f, COR_PRIMARIA, bold = true)
        val largura = pTexto.measureText(texto) + 16f
        canvas.drawRoundRect(RectF(x, y, x + largura, y + 20f), 10f, 10f, pFundo)
        canvas.drawRoundRect(RectF(x, y, x + largura, y + 20f), 10f, 10f, pBorda)
        canvas.drawText(texto, x + 8f, y + 14f, pTexto)
        return y + 22f
    }

    private fun desenharRodape(canvas: Canvas, pagina: Int) {
        val pLinha = Paint().apply { color = COR_PRIMARIA; strokeWidth = 1f }
        canvas.drawLine(MARGIN, PAGE_H - 30f, PAGE_W - MARGIN, PAGE_H - 30f, pLinha)

        val pTexto = paintTexto(9f, COR_SECUNDARIO)
        canvas.drawText("Livro de Receitas  |  ${dataAtual()}", MARGIN, PAGE_H - 16f, pTexto)

        val pPag = paintTexto(9f, COR_SECUNDARIO)
        pPag.textAlign = Paint.Align.RIGHT
        canvas.drawText("Pág. $pagina", PAGE_W - MARGIN, PAGE_H - 16f, pPag)
    }

    private fun quebrarLinhas(texto: String, largMax: Float, paint: Paint): List<String> {
        val resultado = mutableListOf<String>()
        for (paragrafo in texto.split("\n")) {
            if (paragrafo.isBlank()) {
                resultado.add("")
                continue
            }
            val palavras = paragrafo.split(" ")
            var linhaAtual = ""
            for (palavra in palavras) {
                val teste = if (linhaAtual.isEmpty()) palavra else "$linhaAtual $palavra"
                if (paint.measureText(teste) <= largMax) {
                    linhaAtual = teste
                } else {
                    if (linhaAtual.isNotEmpty()) resultado.add(linhaAtual)
                    linhaAtual = palavra
                }
            }
            if (linhaAtual.isNotEmpty()) resultado.add(linhaAtual)
        }
        return resultado
    }

    private fun drawTextWrapped(
        canvas: Canvas, texto: String, x: Float, y: Float,
        largMax: Float, paint: Paint
    ): Float {
        var curY = y
        for (linha in quebrarLinhas(texto, largMax, paint)) {
            canvas.drawText(linha, x, curY, paint)
            curY += paint.textSize * 1.4f
        }
        return curY
    }

    private fun paintTexto(size: Float, color: Int, bold: Boolean = false) = Paint().apply {
        textSize = size
        this.color = color
        isFakeBoldText = bold
        isAntiAlias = true
    }

    private fun salvarPdf(context: Context, doc: PdfDocument, nome: String): File {
        val dir = File(context.getExternalFilesDir(null), "receitas").also { it.mkdirs() }
        val arquivo = File(dir, "$nome.pdf")
        doc.writeTo(FileOutputStream(arquivo))
        doc.close()
        return arquivo
    }

    private fun abrirPdf(context: Context, arquivo: File) {
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.provider",
            arquivo
        )

        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/pdf")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NO_HISTORY)
        }

        val chooser = Intent.createChooser(intent, "Abrir PDF / Imprimir")
        chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        Toast.makeText(context, "PDF gerado: ${arquivo.name}", Toast.LENGTH_SHORT).show()
        context.startActivity(chooser)
    }

    private fun dataAtual(): String =
        SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("pt", "BR")).format(Date())
}