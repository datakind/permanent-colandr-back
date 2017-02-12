package org.datakind.ci.pdfestrian.scripts

object IntervMap {
  val map = Map("area_mgmt" -> "area management",
    "area_protect" -> "area protection",
    "sub" -> "substitution",
    "training" -> "training",
    "restoration" -> "restoration",
    "sus_use" -> "sustainable use",
    "legis" -> "legislation",
    "form_ed" -> "formal education",
    "aware_comm" -> "awareness and communications",
    "compl_enfor" -> "compliance and enforcement",
    "inst_civ_dev" -> "institutional and civil society development",
    "market" -> "market forces",
    "non_mon" -> "non-monetary values",
    "other" -> "other",
    "pol_reg" -> "policies and regulations",
    "priv_codes" -> "private sector standards and codes",
    "sp_control" -> "species control",
    "sp_mgmt" -> "species management",
    "sp_recov" -> "species recovery",
    "sp_reint" -> "species re-introduction",
    "cons_fin" -> "conservation finance",
    "inst_civ_dev" -> "institutional and civil society development",
    "part_dev" -> "partnership and alliance development",
    "liv_alt" -> "enterprises and livelihood alternatives",
    "res_mgmt" -> "resource protection and management")

  def apply(s : String) : String = map.getOrElse(s, "other")
}
