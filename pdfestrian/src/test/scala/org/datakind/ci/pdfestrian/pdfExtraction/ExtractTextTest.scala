package org.datakind.ci.pdfestrian.pdfExtraction
import org.scalatest._

class ExtractTextTest extends FlatSpec with Matchers {

  "Text extraction" should "extract simple test" in {
     ExtractText.extractText(getClass.getResourceAsStream("/test.pdf")).trim should be ("test document")
  }

}
