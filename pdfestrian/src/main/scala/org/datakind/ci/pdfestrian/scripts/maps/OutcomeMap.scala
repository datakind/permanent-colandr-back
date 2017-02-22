package org.datakind.ci.pdfestrian.scripts.maps

/**
  * Created by sameyeam on 2/6/17.
  */
object OutcomeMap {
 val map = Map("free_choice" -> "freedom of choice/action",
    "other" -> "other",
    "culture" -> "cultural and spiritual",
    "health" -> "health",
    "eco_liv_std" -> "economic living standards",
    "mat_liv_std" -> "material living standards",
    "sec_saf" -> "security and safety",
    "sub_well" -> "subjective well-being",
    "education" -> "education",
    "soc_rel" -> "social relations",
    "env" -> "environment",
    "gov" -> "governance and empowerment",
    "NA" -> "other")

  def apply(s : String) : String = map.getOrElse(s, "other")
}