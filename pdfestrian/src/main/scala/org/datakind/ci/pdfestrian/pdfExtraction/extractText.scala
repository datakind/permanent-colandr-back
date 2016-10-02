package org.datakind.ci.pdfestrian.pdfExtraction

import java.io.{File, FileInputStream}

import org.apache.pdfbox.pdfparser.{PDFParser, PDFStreamParser}
import org.apache.pdfbox.pdmodel.PDDocument
import org.apache.pdfbox.text.PDFTextStripper
import org.apache.pdfbox.tools.PDFText2HTML

/**
  * Created by sam on 10/2/16.
  */
object extractText {

  def extractText(filename : String) : String = {
    val stream = PDDocument.load(new File(filename))
    val textExtractor = new PDFTextStripper
    textExtractor.getText(stream)
  }

  def extractHTML(filename : String) : String = {
    val stream = PDDocument.load(new File(filename))
    val textExtractor = new PDFText2HTML
    textExtractor.getText(stream)
  }
}
