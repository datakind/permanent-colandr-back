package org.datakind.ci.pdfestrian.extraction

import java.io._

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend.{LinearMulticlassClassifier, _}
import cc.factorie.app.classify.{Classification => _, _}
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la._
import cc.factorie.model.{DotTemplateWithStatistics2, Parameters}
import cc.factorie.optimize.OptimizableObjectives.Multiclass
import cc.factorie.optimize._
import cc.factorie.util.{BinarySerializer, DoubleAccumulator}
import cc.factorie.variable._
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.api.{Metadata, MetadataExtractor, Record}
import org.datakind.ci.pdfestrian.scripts.{Aid, AidSeq, Interv}

import scala.collection.mutable
import scala.collection.mutable.ArrayBuffer
import scala.io.Source
import scala.reflect.ClassTag
import scala.util.Random

object IntervMap {
  val map = Map("area_protect" -> "Land/Water Protection",
    "legis" -> "Law & Policy",
    "pol_reg" -> "Law & Policy",
    "sp_mgmt" -> "Species Management",
    "res_mgmt" -> "Resource Management",
    "restoration" -> "Land/Water Management",
    "liv_alt" -> "Livelihood, Economic, & Other Incentives",
    "sus_use" -> "Sustainable Use",
    "area_mgmt" -> "Land/Water Management",
    "aware_comm" -> "Education & Awareness",
    "form_ed" -> "Education & Awareness",
    "training" -> "Education & Awareness",
    "cons_fin" -> "External Capacity Building",
    "inst_civ_dev" -> "External Capacity Building",
    "sp_control" -> "Land/Water Management",
    "market" -> "Livelihood, Economic, & Other Incentives",
    "compl_enfor" -> "Law & Policy",
    "part_dev" -> "External Capacity Building",
    "non_mon" -> "Livelihood, Economic, & Other Incentives",
    "priv_codes" -> "Law & Policy",
    "other" -> "?",
    "sp_reint" -> "Species Management",
    "sub" -> "Livelihood, Economic, & Other Incentives",
    "sp_recov" -> "Species Management"
  )
  def apply(s : String) = map.getOrElse(s,"?")
}

object IntervRanker {
  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }

  def intervExtract(aid : AidSeq) : Seq[String] = {
    aid.interv match {
      case a : Seq[Interv] if a.isEmpty => Seq()
      case a: Seq[Interv] =>
        a.map(_.Int_type).map{a => IntervMap(a)}.distinct
    }
  }

  def main(args: Array[String]): Unit = {
    val trainer = new RankTrainer(intervExtract)
    trainer.train(args.head, "intervRankerTest")
  }


}

class IntervClassifier(val modelLoc : String) extends MetadataExtractor {
  val dis = new DataInputStream(new BufferedInputStream(getClass.getResourceAsStream(modelLoc)))
  val ranker = Ranker.deserialize(modelLoc)
  val domain = ranker.domain.categories
  def getMetaData(record : Record, m : String) : Seq[Metadata] = {
    val (d, _) = PDFToDocument.fromString(record.content, record.filename)
    ranker.classify(d).map { r =>
      Metadata(record.id.toString, "interv", r._1, r._2, r._3, r._4)
    }
  }
  def getSentences(record: Record, m : String) : Seq[SentenceClassifications] = {
    val (d, _) = PDFToDocument.fromString(record.content, record.filename)
    ranker.classifySentences(d)
  }
}

object IntervClassifier {
  def main(args: Array[String]): Unit = {
    val doc = Source.fromFile(args.head)
    val record = Record(1,1,1,args.head,doc.getLines().mkString(""))
    val interv = new IntervClassifier("/intervRankerTest")
    println(interv.getMetaData(record, ""))
  }
}