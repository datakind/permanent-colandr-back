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
import org.datakind.ci.pdfestrian.scripts.{Aid, AidSeq, Biome}

import scala.collection.mutable
import scala.collection.mutable.ArrayBuffer
import scala.io.Source
import scala.reflect.ClassTag
import scala.util.Random
object BiomeMap {
  val map = Map("T_T"->"Tundra",
    "T_TSTMBF"->"Forest",
    "T_TSTGSS"->"Grasslands",
    "T_TSTDBF"->"Forest",
    "T_TSTCF"->"Forest",
    "T_TGSS"->"Grasslands",
    "T_TCF"->"Forest",
    "T_TBMF"->"Forest",
    "T_MGS"->"Grasslands",
    "T_MFWS"->"Forest",
    "T_M"->"Mangrove",
    "T_FGS"->"Grasslands",
    "T_DXS"->"Desert",
    "T_BFT"->"Forest",
    "M_TU"->"Marine",
    "M_TSTSS"->"Marine",
    "M_TSS"->"Marine",
    "M_TRU"->"Marine",
    "M_TRC"->"Marine",
    "FW_XFEB"->"Freshwater",
    "FW_TSTUR"->"Freshwater",
    "FW_TSTFRW"->"Freshwater",
    "FW_TSTCR"->"Freshwater",
    "FW_TCR"->"Freshwater",
    "FW_MF"->"Freshwater",
    "FW_LRD"->"Freshwater",
    "FW_LL"->"Freshwater",
    "FW_TFRW"->"Freshwater",
    "FW_TUR" -> "Freshwater"
  )

  def apply(s : String) = map(s)
}

object BiomeRanker {
  def biomeExtract(aid : AidSeq) : Seq[String] = {
    aid.biome match {
      case a : Seq[Biome] if a.isEmpty => Seq()
      case a: Seq[Biome] =>
        a.map(_.biome).map{a => BiomeMap(a)}.distinct
    }
  }

  def main(args: Array[String]): Unit = {
    val trainer = new RankTrainer(biomeExtract)
    trainer.train(args.head, "biomeRankerTest")
  }

}

class BiomeClassifier(val modelLoc : String) extends MetadataExtractor {
  val dis = new DataInputStream(new BufferedInputStream(getClass.getResourceAsStream(modelLoc)))
  val ranker = Ranker.deserialize(modelLoc)
  val domain = ranker.domain.categories
  def getMetaData(record : Record, m : String) : Seq[Metadata] = {
    val (d, _) = PDFToDocument.fromString(record.content, record.filename)
    ranker.classify(d).map { r =>
      Metadata(record.id.toString, "biome", r._1, r._2, r._3, r._4)
    }
  }
  def getSentences(record: Record, m : String) : Seq[SentenceClassifications] = {
    val (d, _) = PDFToDocument.fromString(record.content, record.filename)
    ranker.classifySentences(d)
  }
}

object BiomeClassifier {
  def main(args: Array[String]): Unit = {
    val doc = Source.fromFile(args.head)
    val record = Record(1, 1, 1, args.head, doc.getLines().mkString(""))
    val biome = new BiomeClassifier("/biomeRankerTest")
    println(biome.getMetaData(record, ""))
  }
}