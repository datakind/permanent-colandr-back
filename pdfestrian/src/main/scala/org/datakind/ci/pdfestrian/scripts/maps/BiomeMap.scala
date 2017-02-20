package org.datakind.ci.pdfestrian.scripts.maps

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
