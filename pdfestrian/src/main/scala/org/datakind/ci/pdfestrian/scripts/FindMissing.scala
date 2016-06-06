package org.datakind.ci.pdfestrian.scripts

import java.io.{BufferedWriter, File, FileInputStream, FileWriter}

import org.datakind.ci.pdfestrian.{BiblioItem, PDFExtractedData}

/**
  * Created by samanzaroot on 5/20/16.
  */
object FindMissing {

  def main(args: Array[String]) {
    val bibs = BiblioItem.load(new FileInputStream(args.head))
    val matchedAids = PDFExtractedData.load(new FileInputStream(args.last)).map{ _.aid.get}.toSet
    val unmatchedBibs = bibs.filter( b => !matchedAids.contains(b.aid))
    val out = new BufferedWriter(new FileWriter("unmatchedBibs.json"))
    unmatchedBibs.foreach( b =>
      out.write(b.toJson + "\n")
    )
    out.flush()
  }
}

object MatchUnmatched {

  val yearMatch = ".*([0-9]{4}).*".r

  def main(args: Array[String]) {
    val filenames = new File(args.head).listFiles().filter(_.getAbsolutePath.endsWith("pdf")).map{ l =>
      l.getAbsolutePath.split("/").last
    }
    val authorYears = filenames.flatMap{ file =>
      val f = yearMatch.findFirstMatchIn(file)
      if(f.isEmpty) None
      else {
        val year = f.get.group(1)
        val authort = file.take(file.indexOf(year)-1).toLowerCase
        val authort2 = if(authort.contains("et al")) authort.take(authort.indexOf("et al")-1) else authort
        val author = if(authort2.contains(" and ")) authort2.take(authort.indexOf(" and ")) else authort2
        Some((file,year, author))
      }
    }
    val found = new BufferedWriter(new FileWriter("filematched.json"))
    val notfound = new BufferedWriter(new FileWriter("fileunmatched.json"))
    val unmatchedBibs = BiblioItem.load(new FileInputStream(args.last))
     unmatchedBibs.foreach { un =>
       var wasFound = false
       for(ay <- authorYears) {
        if(un.Authors.toLowerCase.startsWith(ay._3 + ",") && un.Pub_year == ay._2) {
           found.write( PDFExtractedData(ay._1, ay._2.toInt, "","","",Some(un.aid)).toJson + "\n")
          wasFound = true
        }
      }
       if(!wasFound)
         notfound.write(un.toJson + "\n")
    }
    found.flush()
    notfound.flush()
  }
}
