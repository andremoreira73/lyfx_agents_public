## Django settings
#from django.conf import settings
##


## our files


##################################################################
# this is a format that HAS TO BE like this
# After customizing a prompt, we pass the returned "create_prompt" function to the LG pre-defined agent
def customize_function_create_prompt(custom_system_prompt):
    def create_prompt(state):
        return [
            {
                "role": "system", 
                "content": custom_system_prompt
            }
        ] + state['messages']
    return create_prompt


##################################################################
# For our "database": we can use the llm for this, since this is 
# a fairly small list

list_of_chemicals = """
| Chemical | GWP |
| ----- | ----- |
| (E)-HFC-1225ye | 1 |
| (Z)-1,1,1,4,4,4-Hexafluoro-2-butene | 2 |
| 1-Bromopropane | 0.052 |
| 1-Butanol, 2,2,3,3,4,4,4-heptafluoro- | 34 |
| 1-Chlorobutane | 0.007 |
| 1-Ethoxy-1,1,2,2,3,3,3-heptafluoropropane | 61 |
| 1-Ethoxy-1,1,2,3,3,3-hexafluoropropane | 23 |
| 1-Hexene, 3,3,4,4,5,5,6,6,6-nonafluoro- | 1 |
| 1-Octene, 3,3,4,4,5,5,6,6,7,7,8,8,8-tridecafluoro- | 1 |
| 1-Propanol, 2,2,3,3-tetrafluoro- | 13 |
| 1-Propanol, 2,2,3,3,3-pentafluoro- | 19 |
| 1-Propene, 1-chloro-3,3,3-trifluoro-, (1E)- | 1 |
| 1-Propene, 1,2,3,3,3-pentafluoro-, (1Z)- | 1 |
| 1-Propene, 1,3,3,3-tetrafluoro-, (1Z)- | 1 |
| 1-Propene, 2,3,3,3-tetrafluoro- | 1 |
| 1,1-Difluoroethyl 2,2,2-trifluoroacetate | 31 |
| 1,1-Difluoroethyl carbonofluoridate | 27 |
| 1,1,1-Trichloroethane | 146 |
| 1,1,1,3,3,3-Hexafluoro-2-propanol | 182 |
| 1,1,1,3,3,3-Hexafluoropropan-2-yl formate | 333 |
| 1,1,2-Trifluoro-2-(trifluoromethoxy)-ethane | 1240 |
| 1,1,2,2-Tetrafluoro-1-methoxyethane | 359 |
| 1,1,2,2-Tetrafluoro-3-methoxy-propane | 1 |
| 1,1,3,3,4,4,6,6,7,7,9,9,10,10,12,12,13,13,15,15-eicosafluoro-2,5,8,11,14-Pentaoxapentadecane | 3630 |
| 1,2-Dibromo-1,1,2,2-tetrafluoroethane | 1640 |
| 1,2-Dichloroethane | 1 |
| 1,2,2,2-Tetrafluoroethyl formate | 470 |
| 1H-Heptafluoropropane | 2640 |
| 1H,1H,3H-Perfluorobutanol | 17 |
| 2-Bromo-1,1,1-trifluoroethane | 173 |
| 2-Bromo-1,1,1,2-tetrafluoroethane | 184 |
| 2-Chloro-1,1,2-trifluoro-1-methoxyethane | 122 |
| 2-Chloroethyl vinyl ether | 0 |
| 2-Chloropropane | 0.181 |
| 2-Ethoxy-3,3,4,4,5-pentafluorotetrahydro-2,5-bis\[1,2,2,2-tetrafluoro-1-(trifluoromethyl)ethyl\]-furan | 56 |
| 2-Fluoroethanol | 1 |
| 2,2-Difluoroethanol | 3 |
| 2,2,2-Trifluoroethanol | 20 |
| 2,2,2-Trifluoroethyl 2,2,2-trifluoroacetate | 7 |
| 2,2,2-Trifluoroethyl formate | 33 |
| 2,2,2-Trifluoroethyl trifluoromethyl ether | 979 |
| 3-Butenenitrile | 0.002 |
| 3-Pentanone, 1,1,1,2,2,4,5,5,5-nonafluoro-4-(trifluoromethyl)- | 1 |
| 3,3,3-Trifluoro-1-propene | 1 |
| 3,3,3-Trifluoropropan-1-ol | 1 |
| 3,3,3-Trifluoropropyl formate | 17 |
| 3,3,4,4,5,5,6,6,7,7,7-Undecafluoroheptan-1-ol | 1 |
| 3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,11-Nonadecafluoroundecan-1-ol | 1 |
| 3,3,4,4,5,5,6,6,7,7,8,8,9,9,9-Pentadecafluorononan-1-ol | 1 |
| 4,4,4-Trifluorobutan-1-ol | 1 |
| Acetic acid, trifluoro-, methyl ester | 52 |
| Bromodifluoromethane | 376 |
| Bromoethane | 0.487 |
| Butane | 0.006 |
| Butane, 1,1,1,2,2,3,3,4,4-nonafluoro-4-methoxy- | 297 |
| Carbon dioxide | 1 |
| Carbon tetrachloride | 1400 |
| Carbon tetrafluoride | 7390 |
| CFC-11 | 4750 |
| CFC-112 | 4620 |
| CFC-113 | 6130 |
| CFC-113a | 3930 |
| CFC-114 | 10000 |
| CFC-114a | 7420 |
| CFC-115 | 7370 |
| CFC-12 | 10900 |
| CFC-13 | 14400 |
| Chloroethane | 0.481 |
| Chlorofluorocarbons | 0 |
| Chloroform | 16 |
| Chloromethane | 13 |
| Crotonaldehyde | 0 |
| Dibromodifluoromethane | 231 |
| Dibromomethane | 1 |
| Difluoro(fluoromethoxy)methane | 751 |
| Difluoro(methoxy)methane | 144 |
| Difluoromethyl 2,2,2-trifluoroacetate | 27 |
| Dimethyl ether | 1 |
| Dimethyldifluoromethane | 144 |
| Enflurane | 583 |
| Ethane | 0.437 |
| Ethane, (trifluoromethoxy)- | 29 |
| Ethane, 1-(difluoromethoxy)-1,1,2,2-tetrafluoro- | 4240 |
| Ethane, 1-ethoxy-1,1,2,2-tetrafluoro- | 627 |
| Ethane, 1,1-dichloro-1,2-difluoro- | 338 |
| Ethane, 1,1-difluoro-2-(trifluoromethoxy)- | 828 |
| Ethane, 1,1,1-trifluoro-2-methoxy- | 1 |
| Ethane, 1,1,1,2-tetrafluoro-2-(trifluoromethoxy)- | 6450 |
| Ethane, 1,1,1,2,2-pentafluoro-2-methoxy- | 708 |
| Ethane, 1,1,2,2-tetrafluoro-1-(fluoromethoxy)- | 871 |
| Ethane, 1,2-dichloro-1-fluoro- | 46.6 |
| Ethane, 2-(difluoromethoxy)-1,1,1-trifluoro- | 659 |
| Ethane, 2-(difluoromethoxy)-1,1,1,2-tetrafluoro-, (+-)- | 1790 |
| Ethene, (2,2,2-trifluoroethoxy)- | 1 |
| Ethyl nonafluorobutyl ether | 59 |
| Ethyl trifluoroacetate | 1 |
| Ethylene dibromide | 1.02 |
| Fluoro(fluoromethoxy)methane | 617 |
| Fluoro(methoxy)methane | 13 |
| Halon 1011 | 4.74 |
| Halon 1211 | 1890 |
| Halon 1301 | 7140 |
| Halothane | 41 |
| HCFC-121 | 58.3 |
| HCFC-122 | 59 |
| HCFC-122a | 258 |
| HCFC-123 | 77 |
| HCFC-123a | 370 |
| HCFC-124 | 609 |
| HCFC-124a | 2070 |
| HCFC-132 | 122 |
| HCFC-133a | 388 |
| HCFC-141b | 725 |
| HCFC-142b | 2310 |
| HCFC-21 | 148 |
| HCFC-22 | 1810 |
| HCFC-225ca | 122 |
| HCFC-225cb | 595 |
| HCFC-31 | 79.4 |
| Hexafluoro-1,3-butadiene | 1 |
| Hexafluoroethane | 12200 |
| Hexafluoropropene | 1 |
| HFC-1234ze(E) | 1 |
| HFC-125 | 3500 |
| HFC-134 | 1120 |
| HFC-1345zfc | 1 |
| HFC-134a | 1430 |
| HFC-143 | 328 |
| HFC-143a | 4470 |
| HFC-152 | 16 |
| HFC-152a | 124 |
| HFC-161 | 4 |
| HFC-227ea | 3220 |
| HFC-23 | 14800 |
| HFC-236cb | 1210 |
| HFC-236ea | 1330 |
| HFC-236fa | 9810 |
| HFC-245ca | 716 |
| HFC-245cb | 4620 |
| HFC-245ea | 235 |
| HFC-245eb | 290 |
| HFC-245fa | 1030 |
| HFC-32 | 675 |
| HFC-329p | 2360 |
| HFC-365mfc | 794 |
| HFC-41 | 116 |
| HFC-4310mee | 1640 |
| HFE 7100 | 460 |
| HFE-329mcc2 | 3070 |
| HFE-329me3 | 4550 |
| HFE-338mcf2 | 929 |
| HFE-338mmz1 | 2620 |
| HFE-338pcc13 (HG-01) | 1500 |
| HFE-347mcf2 | 854 |
| HFE-347mmy1 | 363 |
| HFE-347pcf2 | 580 |
| HFE-356mec3 | 387 |
| HFE-356mff2 | 17 |
| HFE-356mmz1 | 14 |
| HFE-356pcc3 | 110 |
| HFE-356pcf2 | 719 |
| HFE-356pcf3 | 446 |
| HFE-365mcf2 | 58 |
| HFE-365mcf3 | 1 |
| HG-02 | 2730 |
| HG-03 | 2850 |
| HG-20 | 5300 |
| HG-21 | 3890 |
| HG-30 | 1870 |
| HG'-01 | 202 |
| HG'-02 | 236 |
| HG'-03 | 221 |
| Hydrochlorofluorocarbons | 0 |
| Hydrofluorocarbons | 0 |
| Isoflurane | 350 |
| Methane | 25 |
| Methane, (difluoromethoxy)trifluoro- | 14900 |
| Methane, bis(difluoromethoxy)difluoro- | 2800 |
| Methane, oxybis\[difluoro- | 6320 |
| Methane, trifluoromethoxy- | 756 |
| Methyl 2,2-difluoroacetate | 3 |
| Methyl bromide | 5 |
| Methyl carbonofluoridate | 95 |
| Methyl vinyl ketone | 0 |
| Methylene chloride | 8.7 |
| Nitrogen trifluoride | 17200 |
| Nitrous oxide | 298 |
| Octafluorocyclopentene | 2 |
| Octamethylcyclotetrasiloxane | 0.739 |
| Octane, octadecafluoro- | 7620 |
| Perfluorobut-1-ene | 1 |
| Perfluorobut-2-ene | 2 |
| Perfluorobutane | 8860 |
| Perfluorobutyl acetate | 2 |
| Perfluorobutyl formate | 392 |
| Perfluorocyclobutane | 10300 |
| Perfluorodecalin | 7500 |
| Perfluorodecalin (cis) | 7240 |
| Perfluorodecalin (trans) | 6290 |
| Perfluoroethyl acetate | 2 |
| Perfluoroethyl formate | 580 |
| Perfluoroheptane | 7820 |
| Perfluorohexane | 9300 |
| Perfluorooctyl Ethylene | 0.141 |
| Perfluoropentane | 9160 |
| Perfluoropropane | 8830 |
| Perfluoropropyl acetate | 2 |
| Perfluoropropyl formate | 376 |
| Propanal, 3,3,3-trifluoro- | 1 |
| Propane | 0.02 |
| Propane, 1,1,1-trifluoro- | 76 |
| Propane, 1,1,1,2,2,3,3-heptafluoro-3-(1,2,2,2-tetrafluoroethoxy)- | 6490 |
| Propane, 1,1,1,2,2,3,3-heptafluoro-3-methoxy- | 575 |
| Propane, 2-(difluoromethoxymethyl)-1,1,1,2,3,3,3-heptafluoro- | 437 |
| Propane, 2-(ethoxydifluoromethyl)-1,1,1,2,3,3,3-heptafluoro- | 34.3 |
| Sevoflurane | 216 |
| Sulfur hexafluoride (SF6) | 22800 |
| Sulfuryl fluoride (SF) | 4090 |
| Tetrachloroethylene | 6.34 |
| Tetrafluoroethene | 1 |
| Tribromomethane | 0.25 |
| Trichloroethylene | 0.044 |
| Trifluoro(fluoromethoxy)methane | 222 |
| Trifluoro(trifluoromethoxy)ethylene | 1 |
| Trifluoromethyl acetate | 2 |
| Trifluoromethyl formate | 588 |
| Trifluoromethyl sulfur pentafluoride | 17700 |
| Vinyl fluoride | 1 |
| Vinylidene fluoride | 1 |
"""