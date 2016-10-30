package org.datakind.ci.pdfestrian.extraction

import java.io._
import cc.factorie.app.classify.{Classification => _, _}
import org.datakind.ci.pdfestrian.api.{Metadata, MetadataExtractor, Record}
import org.datakind.ci.pdfestrian.scripts.{AidSeq,  Outcome}
import org.json4s.NoTypeHints
import org.json4s.jackson.Serialization
import scala.io.Source

object OutcomeRanker {
  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }

  def outcomeExtract(aid : AidSeq) : Seq[String] = {
    aid.outcome match {
      case a : Seq[Outcome] if a.isEmpty => Seq()
      case a: Seq[Outcome] =>
        a.map(_.Outcome).distinct
    }
  }

  def main(args: Array[String]): Unit = {
    val trainer = new RankTrainer(outcomeExtract)
    trainer.train(args.head, "OutcomeRankerTest")
  }

}

class OutcomeClassifier(val modelLoc : String) extends MetadataExtractor {
  val dis = new DataInputStream(new BufferedInputStream(getClass.getResourceAsStream(modelLoc)))
  val ranker = Ranker.deserialize(modelLoc)
  val domain = ranker.domain.categories
  def getMetaData(record : Record, m : String) : Seq[Metadata] = {
    val (d, _) = PDFToDocument.fromString(record.content, record.filename)
    ranker.classify(d).map { r =>
      Metadata(record.id.toString, "outcome", r._1, r._2, r._3, r._4)
    }
  }
  def getSentences(record: Record, m : String) : Seq[SentenceClassifications] = {
    val (d, _) = PDFToDocument.fromString(record.content, record.filename)
    ranker.classifySentences(d)
  }
}

object OutcomeClassifier {
  implicit val formats = Serialization.formats(NoTypeHints)
  import org.json4s.jackson.Serialization.write

  def main(args: Array[String]): Unit = {
    val doc = Source.fromFile(args.head)
    val record = Record(1,1,1,args.head,doc.getLines().mkString(""))
    val outcome = new OutcomeClassifier("/OutcomeRankerTest")
    println(write(outcome.getMetaData(record, "")))
  }
}