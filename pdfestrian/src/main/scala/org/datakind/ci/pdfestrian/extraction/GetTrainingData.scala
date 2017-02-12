package org.datakind.ci.pdfestrian.extraction

/**
  * Created by sameyeam on 2/8/17.
  */
class GetTrainingData {
   val query = "select * from data_extractions as de inner join fulltexts as f on f.\nid=de.id where extracted_items != '{}' and extracted_items != '[]' and f.review_id=?"
}
