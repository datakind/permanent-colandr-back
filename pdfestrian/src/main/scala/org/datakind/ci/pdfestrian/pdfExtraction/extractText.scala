package org.datakind.ci.pdfestrian.pdfExtraction

import java.io.{BufferedWriter, File, FileWriter}

import org.apache.pdfbox.pdmodel.PDDocument
import org.apache.pdfbox.text.PDFTextStripper
import org.apache.pdfbox.tools.PDFText2HTML

import scala.tools.nsc.interpreter.InputStream

object ExtractText {

  /**
    * Extracts text from PDF.
    * @param filename file path of PDF to extract
    * @return fulltext extracted from PDF if possible
    */
  def extractText(filename : String) : String = {
    try {
      val file = new File(filename)
      if(!file.exists()) {
        sys.error("File doesn't exist")
        return ""
      }
      val stream = PDDocument.load(file)
      val textExtractor = new PDFTextStripper
      val txt = textExtractor.getText(stream)
      stream.close()
      txt
    } catch {
      case e : Exception => ""
    }
  }

  /**
    * Extracts text from PDF inputstream.
    * @param inputstream inputstream of PDF to extract
    * @return fulltext extracted from PDF if possible
    */
  def extractText(inputstream : InputStream) : String = {
    try {
      val stream = PDDocument.load(inputstream)
      val textExtractor = new PDFTextStripper
      val txt = textExtractor.getText(stream)
      stream.close()
      txt
    } catch {
      case e : Exception => ""
    }
  }


  /**
    * Extracts HTML version of PDF from PDF.
    * @param filename file path of PDF to extract
    * @return HTML version of PDF if possible
    */
  def extractHTML(filename : String) : String = {
    try {
      val file = new File(filename)
      if(!file.exists()) {
        println("File doesn't exist")
        return ""
      }
      val stream = PDDocument.load(file)
      val textExtractor = new PDFText2HTML
      val html = textExtractor.getText(stream)
      stream.close()
      html
    } catch {
      case e : Exception => ""
    }
  }

  case class ExtractTextConfig(filename : String = "", html : Boolean = false)
  val parser = new scopt.OptionParser[ExtractTextConfig]("extractText") {
    head("extractText", "0.1")

    opt[String]('f', "filename").required().action((x, c) =>
      c.copy(filename = x)).text("Filename of pdf")

    opt[Unit]('h', "html").
      action((x, c) => c.copy(html = true)).
      text("flag, if on will extract html string instead of plain text")
  }

  def main(args : Array[String]) : Unit = {
    parser.parse(args, ExtractTextConfig()) match {
      case Some(config) =>
        if(config.html) println(extractHTML(config.filename))
        else println(extractText(config.filename))
      case None =>
        println("")
    }
  }
}

object ExtractTextDirectory {
  def main (args: Array[String] ): Unit = {
    val dir = new File(args.head)
    for(file <- dir.listFiles(); if file.getAbsolutePath.endsWith(".pdf")) {
      val out = new BufferedWriter(new FileWriter(file.getAbsolutePath + ".txt"))
      out.write(ExtractText.extractText(file.getAbsolutePath))
      out.flush()
      out.close()
    }
  }
}

object ExtractHtmlDirectory {
  def main (args: Array[String] ): Unit = {
    val dir = new File(args.head)
    for(file <- dir.listFiles(); if file.getAbsolutePath.endsWith(".pdf")) {
      val out = new BufferedWriter(new FileWriter(file.getAbsolutePath + ".html"))
      out.write(ExtractText.extractHTML(file.getAbsolutePath))
      out.flush()
      out.close()
    }
  }
}