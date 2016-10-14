package org.datakind.ci.pdfestrian.pdfExtraction

import java.io.{BufferedWriter, File, FileInputStream, FileWriter}

import org.apache.pdfbox.pdfparser.{PDFParser, PDFStreamParser}
import org.apache.pdfbox.pdmodel.PDDocument
import org.apache.pdfbox.text.PDFTextStripper
import org.apache.pdfbox.tools.PDFText2HTML

/**
  * Created by sam on 10/2/16.
  */
object extractText {

  def extractText(filename : String) : String = {
    try {
      val file = new File(filename)
      if(!file.exists()) {
        println("File doesn't exist")
        return ""
      }
      val stream = PDDocument.load(file)
      val textExtractor = new PDFTextStripper
      textExtractor.getText(stream)
    } catch {
      case e : Exception => ""
    }
  }

  def extractHTML(filename : String) : String = {
    try {
      val file = new File(filename)
      if(!file.exists()) {
        println("File doesn't exist")
        return ""
      }
      val stream = PDDocument.load(file)
      val textExtractor = new PDFText2HTML
      textExtractor.getText(stream)
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

object extractTextDirectory {
  def main (args: Array[String] ): Unit = {
    val dir = new File(args.head)
    for(file <- dir.listFiles(); if file.getAbsolutePath.endsWith(".pdf")) {
      val out = new BufferedWriter(new FileWriter(file.getAbsolutePath + ".txt"))
      out.write(extractText.extractText(file.getAbsolutePath))
      out.flush()
      out.close()
    }
  }
}

object extractHtmlDirectory {
  def main (args: Array[String] ): Unit = {
    val dir = new File(args.head)
    for(file <- dir.listFiles(); if file.getAbsolutePath.endsWith(".pdf")) {
      val out = new BufferedWriter(new FileWriter(file.getAbsolutePath + ".html"))
      out.write(extractText.extractHTML(file.getAbsolutePath))
      out.flush()
      out.close()
    }
  }
}