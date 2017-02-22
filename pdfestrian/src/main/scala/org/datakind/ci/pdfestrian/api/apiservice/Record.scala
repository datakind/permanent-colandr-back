package org.datakind.ci.pdfestrian.api.apiservice

/**
  * A representation of DB record of a citation in a review
  * @param id id of the citation
  * @param reviewId id of the review of this citation
  * @param citationId the citation id (should be the same as id)
  * @param filename the filename of the pdf of the citation
  * @param content the fulltext content extracted from the PDF
  */
case class Record(id : Int, reviewId : Int, citationId : Int, filename : String, content : String)
