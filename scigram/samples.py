"""
Built-in scientific manuscript presets for testing SciGram's 3-tier
Pangram-style passage detection (Human-Written, AI-Assisted, AI-Generated)
and interactive Structural Revision Studio.
"""

from __future__ import annotations

from typing import List, Dict


PRESET_SAMPLES: List[Dict[str, str]] = [
    {
        "id": "mixed_manuscript",
        "title": "Mixed IMRaD Manuscript (Human + AI-Assisted + AI)",
        "badge": "3-Tier Demo",
        "description": "Multi-section cancer biology draft: AI-generated Introduction, authentic human Methods & Results (CC-BY PLOS Biol. 2018), and AI-polished Discussion.",
        "text": (
            "1. Introduction\n\n"
            "Recent advancements in tumor microenvironment profiling have revolutionized the landscape of metastasis research, "
            "offering unprecedented opportunities to overcome traditional therapeutic limitations. Furthermore, lymphatic "
            "remodeling plays a pivotal role in enhancing metastatic dissemination while simultaneously modulating local immune "
            "surveillance. Moreover, delving into the intricate interplay between endothelial signaling and stromal dynamics "
            "underscores the transformative potential of vascular-targeted interventions, paving the way for next-generation "
            "oncology therapeutics.\n\n"
            "2. Materials and Methods\n\n"
            "Metastatic dissemination employs both the blood and lymphatic vascular systems. Solid tumors dynamically remodel "
            "and generate both vessel types during cancer progression. Deregulated tumor tissue fluid homeostasis and immune "
            "trafficking associated with tumor lymphangiogenesis may contribute to metastatic spreading; however, the precise "
            "functional characterization of lymphatic endothelial cells (LECs) in tumors is challenged by the lack of specific "
            "reagents to decipher their rate-limiting role in metastasis. Therefore, we generated transgenic mice (PDPN "
            "promoter-driven Cre recombinase transgene [PDPN-Cre] and PDPN promoter-driven thymidine kinase transgene [PDPN-tk]) "
            "that allow for the identification and genetically controlled depletion of proliferating podoplanin (Pdpn)-expressing LECs.\n\n"
            "3. Results\n\n"
            "We demonstrate that suppression of lymphangiogenesis is successfully achieved in lymphangioma lesions induced in "
            "the PDPN-tk mice. In multiple metastatic breast cancer mouse models, we identified distinct roles for LECs in "
            "primary and metastatic tumors. Reduced lymphatic vessel density enhanced primary tumor lymphedema and increased "
            "the frequency of intratumoral macrophages, but was not associated with a significant impact on primary tumor growth "
            "despite a marked reduction in metastatic dissemination to axillary lymph nodes and lung parenchyma.\n\n"
            "4. Discussion\n\n"
            "Our findings support the functional contribution of primary tumor lymphangiogenesis in controlling metastasis to "
            "axillary lymph nodes and lung parenchyma, although ganciclovir timing remained critical before day 10 post-implantation. "
            "Furthermore, this selective decoupling of primary tumor burden from distal colonization underscores a promising "
            "avenue for refining anti-lymphangiogenic combination therapies."
        ),
    },
    {
        "id": "ai_generated_intro",
        "title": "AI-Generated Scientific Introduction",
        "badge": "High AI Structure",
        "description": "Classic LLM-structured battery materials introduction exhibiting uniform ~23-word cadence, participial '-ing' tails, and excess vocabulary.",
        "text": (
            "In the rapidly evolving realm of sustainable energy storage, solid-state lithium-metal batteries have garnered "
            "significant attention due to their superior energy density and enhanced safety profiles. Despite these promising "
            "advancements, critical challenges remain regarding interfacial instability and dendrite propagation during high-rate "
            "cycling. Specifically, the intricate interplay between solid electrolyte grain boundaries and mechanical stress "
            "accumulation plays a pivotal role in governing premature cell failure.\n\n"
            "To address these multifaceted limitations, recent studies have leveraged nanoscale surface engineering strategies, "
            "thereby facilitating more uniform lithium-ion transport across the electrode-electrolyte interface. Furthermore, "
            "comprehensive multi-scale modeling frameworks not only illuminate fundamental charge-transfer mechanisms but also "
            "bridge the gap between atomistic simulations and practical cell design. Collectively, these groundbreaking insights "
            "underscore the indispensable value of rational interface design, paving the way for commercially viable next-generation "
            "energy storage technologies."
        ),
    },
    {
        "id": "authentic_human_paper",
        "title": "Authentic Human Empirical Prose",
        "badge": "Human Baseline",
        "description": "Genuine pre-LLM crystallography abstract (CC-BY PLOS Biol. 2018) showing organic burstiness, specific intermediates, and zero LLM clichés.",
        "text": (
            "Tyrosinase (EC 1.14.18.1), a copper-containing monooxygenase, catalyzes the conversion of phenol to the corresponding "
            "ortho-quinone. The Streptomyces tyrosinase is generated as a complex with a caddie protein that transports two copper "
            "ions into the active center. In our previous study, the Tyr98 residue in the caddie protein, which is accommodated in "
            "the pocket of active center of tyrosinase, has been found to be converted to a reactive quinone through the formations "
            "of the peroxo-dicopper(II) and Cu(II)-dopasemiquinone intermediates.\n\n"
            "Until now—despite extensive studies for the tyrosinase reaction based on crystallographic analysis, low-molecular-weight "
            "models, and computer simulations—the catalytic mechanism has been unable to be made clear at an atomic level. In the "
            "present study, cryo-trapped crystal structures were determined at very high resolutions (1.16-1.70 A). The structures "
            "suggest the existence of an important step for the tyrosinase reaction that has not yet been found: that is, the "
            "hydroxylation reaction is triggered by the movement of CuA, which induces the syn-to-anti rearrangement of the copper "
            "ligands after the formation of the peroxo-dicopper(II) core."
        ),
    },
    {
        "id": "latex_manuscript",
        "title": "LaTeX (.tex) Manuscript Snippet",
        "badge": "LaTeX Aware",
        "description": "Demonstrates native LaTeX parsing (\\section, \\cite, inline math) contrasting an empirical Methods section with an AI-generated Conclusion.",
        "text": (
            "\\section{Crystallographic Refinement}\n"
            "Until now, despite extensive studies for the tyrosinase reaction based on crystallographic analysis, "
            "low-molecular-weight models, and computer simulations~\\cite{matoba2018}, the catalytic mechanism has been "
            "unable to be made clear at an atomic level. In the present study, cryo-trapped crystal structures were "
            "determined at very high resolutions ($1.16$--$1.70$~\\AA; Table~\\ref{tab:xray}). The structures suggest the "
            "existence of an important step for the tyrosinase reaction that has not yet been found: the hydroxylation "
            "reaction is triggered by the movement of $\\text{Cu}_A$, which induces the syn-to-anti rearrangement of the "
            "copper ligands.\n\n"
            "\\section{Conclusion}\n"
            "In conclusion, our comprehensive structural investigation showcases remarkable mechanistic clarity across intermediate "
            "catalytic states, highlighting the transformative potential of time-resolved crystallography in enzymology. Furthermore, "
            "delving into these intricate metal-ligand rearrangements not only bolsters bioinorganic theory but also paves the way "
            "for rational biocatalyst engineering."
        ),
    },
]
