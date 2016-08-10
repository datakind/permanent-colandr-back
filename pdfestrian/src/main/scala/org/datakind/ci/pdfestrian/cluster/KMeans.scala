package org.datakind.ci.pdfestrian.cluster

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.Document
import cc.factorie.la.{DenseTensor, DenseTensor1, SparseTensor1}
import org.datakind.ci.pdfestrian.extraction.{PDFToDocument, TfIdf}
import org.datakind.ci.pdfestrian.scripts.{Aid, Biome}

import scala.collection.mutable.ArrayBuffer
import scala.util.Random

/**
  * Created by sameyeam on 8/6/16.
  */
class KMeans(val K : Int, dim : Int) {
  val rand = new Random
  val clusters = Array.fill(K)(new DenseTensor1((0 until dim).map{a => math.abs(rand.nextDouble())}.toArray))
  val counts = Array.fill(K)(0)

  def initialize(all : Array[SparseTensor1]) : Unit = {
    /*var current = 1
    clusters(0) = new DenseTensor1(all(rand.nextInt(all.length)).toArray)
    while (current < K) {
      val allDist  = all.map { st =>
        val d = new DenseTensor1(st.toArray)
        val distances = (0 until current).map{ i => clusters(i).cosineSimilarity(d) }
        distances.max
      }
      val next = allDist.zipWithIndex.minBy(_._1)._2
      clusters(current) = new DenseTensor1(all(next).toArray)
      current += 1
    }*/
    /*for(k <- clusters) {
      println(k.mkString(","))
    }*/
  }

  /*def +=(st : SparseTensor1) : Int = {
    val d = new DenseTensor1(st.toArray)
    val clusterDist = clusters.map{ _.cosineSimilarity(d)}
    val cluster = clusterDist.zipWithIndex.maxBy(_._1)._2
    val currentProb = counts(cluster).toDouble/(counts(cluster).toDouble + 1)
    val nextProb = 1.0/(counts(cluster).toDouble + 1)
    counts(cluster) += 1
    clusters(cluster) = ((clusters(cluster) * currentProb) + (d * nextProb)).asInstanceOf[DenseTensor1]
    cluster
  }*/

  def run(all : Array[SparseTensor1]) : Unit = {
    val mappings = all.zipWithIndex.map{ case(st,i) =>
      predict(st)._1 -> i
    }.groupBy(_._1)
    mappings.foreach{ map =>
      val cluster = map._1
      val sum = map._2.foldRight(new DenseTensor1(TfIdf.featureSize)){ case ((_,i),dt) =>
        dt += all(i)
        dt
      }/map._2.length
      clusters(cluster) = sum.asInstanceOf[DenseTensor1]
    }
  }

  def predict(st : SparseTensor1) : (Int, Double) = {
    val d = new DenseTensor1(st.toArray)
    clusters.map{ _.cosineSimilarity(d)}.zipWithIndex.maxBy(_._1).swap
  }
}

object KMeans {

  def getDocument(a : Aid) : Option[(Aid,Document,SparseTensor1)] = {
    PDFToDocument(a.pdf.filename) match {
      case Some((d,d2)) =>
        Some((a,d,TfIdf(d)))
      case None =>
        None
    }
  }
  var iter = 100
  def main(args: Array[String]): Unit = {
    val data = Aid.load(args.head).flatMap { a =>
      getDocument(a)
    }
    val K = args.last.toInt
    val clusterer = new KMeans(K, TfIdf.featureSize)

    clusterer.initialize(data.map{_._3}.toArray)
    for(i <- 0 until iter) {
      clusterer.run(data.map{_._3}.toArray)
    }
    val clusters = Array.fill(K)(new ArrayBuffer[(String,String,String,Double)]())
    for(d <- data) {
      val (cluster, distance) = clusterer.predict(d._3)
      val point = (d._1.pdf.filename, d._1.bib.Title, d._1.biome.getOrElse(Biome(0,"")).biome, distance)
      clusters(cluster) += point
    }
    for((c,i) <- clusters.zipWithIndex) {
      val out = new BufferedWriter(new FileWriter(s"cluster$i.txt"))
      out.write(c.sortBy(-_._4).map{ a => a._1 + "\t" + a._2 + "\t" + a._3 + "\t" + a._4}.mkString("\n"))
      out.flush()
      out.close()
    }
  }
}
