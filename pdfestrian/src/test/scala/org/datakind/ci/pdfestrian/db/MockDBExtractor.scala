package org.datakind.ci.pdfestrian.db

import org.datakind.ci.pdfestrian.api.apiservice.Record
import org.datakind.ci.pdfestrian.api.apiservice.components.Access
import org.datakind.ci.pdfestrian.trainingData.{Label, MultiValue, TrainingData}

import scala.collection.mutable.ArrayBuffer
import scala.util.Random

object MockDB {
  val map = Map[String, Record](
    "0" -> Record(0, 1, 1, "file1.pdf", "26-foot darcheville pistolesi hickersberger tenebrionoidea semak madcow mitul yabunaka lihd uncorrected socialistic zoroaster 10/8 obelisks ferromagnetic marzipan."),
    "1" -> Record(1, 1, 1, "file2.pdf", "marzipan mcvay joinville distributorship genotypes plessy worst-case choicest powerplants plp 4800 arpeggios hewing devdas ronni."),
    "2" -> Record(2, 1, 1, "file3.pdf", "devdas ronni pdk 1.125 librettos hdnet drewry symbionese vaikundar tactfully forestalled rehiring."),
    "3" -> Record(3, 1, 1, "file4.pdf", "clenching dreamin zwanziger sonnenberg retton citybus pirandello filippi klock valance 30,000-strong kolata goldfrapp zatlers m.h. jinjiang chewbacca mehri."),
    "4" -> Record(4, 1, 1, "file5.pdf", "keath digress avnet snobby pompei tisa christin sipho 28-3 abdelrahman koenigs dificil lampreia rpalmeiro euro680 vandore repubs tanana."),
    "0" -> Record(5, 1, 1, "file6.pdf", "vandore repubs tanana smallholder mesoderm nine-month davitt referent tempus 20k palimpsest macromolecules 43.0 ramla '67 hapag antz monnaie copyist toonami bagration divo.")
  )

  def apply(s : String) = map.get(s)
}

object MockTrainingData {
  val labels = Map[String, Seq[Label]](
    "label1" -> Seq(MultiValue("label1", Array("v1")), MultiValue("label1", Array("v2")),  MultiValue("label1", Array("v3")),
      MultiValue("label1", Array("v4")), MultiValue("label1", Array("v5"))),
    "label2" -> Seq(MultiValue("label2", Array("v2")), MultiValue("label2", Array("v1"))),
    "label3" -> Seq(MultiValue("label3", Array("v1")), MultiValue("label3", Array("v3")), MultiValue("label3", Array("v2")),
      MultiValue("label3", Array("v4")),  MultiValue("label3", Array("v5"))),
    "label4" -> Seq(MultiValue("label4", Array("v2")), MultiValue("label4", Array("v1")),
      MultiValue("label4", Array("v3")))
  )

  val trainingData = ArrayBuffer[TrainingData]()

  private val random = new Random()

  def add() : Unit = {
    if(trainingData.size != MockDB.map.size) {
      val record = MockDB.map(trainingData.size.toString)
      val recordLabels = (0 to random.nextInt(labels.size)).map { label =>
        val lvs = labels.values.toSeq(label)
        lvs(random.nextInt(lvs.length))
      }
      trainingData += TrainingData(record.id, record.content, recordLabels.toArray)
    }
  }

}

/**
  * Created by sameyeam on 2/20/17.
  */
class MockDBExtractor extends Access {
  import MockDB.map
  /**
    * Gets a record from an id
    *
    * @param record record id
    * @return Option, record returned if id exists, None otherwise
    */
  override def getFile(record: String): Option[Record] = {
     map.get(record)
  }

  /**
    * Get all training data from a review
    *
    * @param review the id of the review
    * @return an array of [[TrainingData]] instances
    */
  override def getTrainingData(review: Int): Array[TrainingData] = MockTrainingData.trainingData.toArray

  /**
    * Gets all the training data from the review, but doesn't get the fulltext
    *
    * @param review the id of the review
    * @return an array of [[TrainingData]] instances with empty fulltext content
    */
  override def getTrainingLabels(review: Int): Array[TrainingData] = MockTrainingData.trainingData.map{ td =>
  td.copy(fullText = "")}.toArray
}
