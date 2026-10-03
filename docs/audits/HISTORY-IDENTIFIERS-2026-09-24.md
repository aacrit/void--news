# History identifiers audit, 2026-09-24

Phase 0 of `docs/proposals/HISTORY-THESIS-PAGE.md`, CEO decision 1 as recorded in its section 13: a wrong or dead identifier is stripped from its bibliography entry and the entry is kept, marked `verified: false` when no identifier remains, until the evidence ledger rebuild resolves it. Nothing false stays linked and no real work is lost. This file is the recovery list: every identifier removed, per event, with the reason, so the ledger rebuild can find the real work.

## What was checked

Every distinct DOI in `data/history/events/*.yaml` (239) was resolved through doi.org and looked up on the Crossref API, and the Crossref title and author family names were compared against the entry's own title and author. Where Crossref held no record, the landing page title was read. Every distinct `archive_url` (384) was fetched with a HEAD request. Both passes ran on 2026-09-24.

A DOI was treated as bad only when it hard-404s at doi.org, or when Crossref or the landing page shows a clearly different work: a journal review of the book cited as the book (the Pacific Affairs pattern accounts for most), a chapter of a different book, a different article by the same author, a Choice review, a bibliography entry about the work. A DOI that resolves to a chapter of the same book, a short-title variant of the same work by the same author, a reprint of the same text in an anthology, or a publisher book DOI whose landing page names the work was kept. Eight JSTOR DOIs that resolve but sit behind a bot challenge could not be read either way and were left in place; they are listed at the end. An archive.org link was treated as dead only on a 404; the one that timed out twice (`racingenemy00tsuy`) was left alone.

## Counts

- Bibliography entries touched: 188 in 59 events
- DOI fields stripped: 98 (95 distinct DOIs)
- archive_url fields stripped: 95 (90 distinct dead links)
- Entries now marked `verified: false` (no identifier left): 159
- Entries that lost a bad identifier but keep a live one: 29
- Stock media items removed (Unsplash, Pexels): 242
- Hero images repointed from a removed stock item to a remaining archival item: 9

Reasons for the DOI strips: different work (52), 404 (36), a review, not the work (10).

Two things the pass noticed and did not change, because they are not identifier errors. `partition-of-india` cites "The struggle for Pakistan: a Muslim homeland and global politics, by Ayesha Jalal" by Ishtiaq Ahmed: that is a review of Jalal's book, honestly attributed to the reviewer, and its DOI resolves to that review. `congo-wars` cites Peterman, Palermo and Bredenkamp under the title "Rape in War"; the DOI resolves to their AJPH article, whose real title is "Estimates and Determinants of Sexual Violence Against Women in the Democratic Republic of Congo". Both belong to the ledger rebuild.

## Hero repoints

| slug | removed stock file | now |
|---|---|---|
| `ashoka-maurya-empire` | pexels_1.jpg | https://commons.wikimedia.org/wiki/File:Ashoka_Pillar_at_Vaishali,_Bihar,_India.jpg (Wikimedia Commons, public domain) |
| `holodomor` | unsplash_1.jpg | https://commons.wikimedia.org/wiki/File:Holodomor_Kharkiv.jpg (Alexander Wienerberger, 1933, public domain via Wikimedia Commons) |
| `peloponnesian-war` | pexels_1.jpg | https://commons.wikimedia.org/wiki/File:Peloponnesian_war_alliances_431_BC.png (Marsyas, CC BY-SA 3.0, via Wikimedia Commons) |
| `scramble-for-africa` | unsplash_1.jpg | https://commons.wikimedia.org/wiki/File:Afrikakonferenz.jpg (Adalbert von Rosler, 1884, public domain) |
| `the-crusades` | pexels_1.jpg | https://commons.wikimedia.org/wiki/File:Counquest_of_Jeruslam_%281099%29.jpg (Emile Signol, 1847, public domain) |
| `tiananmen-square` | unsplash_1.jpg | https://en.wikipedia.org/wiki/Tank_Man#/media/File:Tiananmen_square_june5_1989.jpg (Jeff Widener / Associated Press, 1989) |
| `trail-of-tears` | unsplash_1.jpg | https://commons.wikimedia.org/wiki/File:John_Ross_(Cherokee_chief).jpg (Public domain, National Archives) |
| `transatlantic-slave-trade` | unsplash_1.jpg | https://commons.wikimedia.org/wiki/File:Slaveshipposter.jpg (Society for Effecting the Abolition of the Slave Trade, 1788, public domain) |
| `treaty-of-waitangi` | unsplash_1.jpg | https://commons.wikimedia.org/wiki/File:Treatyofwaitangi.jpg (Archives New Zealand, public domain) |

The served page did not change for any of these: `pipeline/history/export_history.py` already refused a non-Commons hero and substituted the event's first verified image, so the YAML now names the picture the page was already showing.

## Stripped identifiers, per event

### `angkor-khmer-empire`

- doi `10.1016/j.quascirev.2010.04.024`: different work: Crossref 'Late Quaternary vegetation and environments in the Verkhoyansk Mountains region (NE Asia) reconstruc' in 'Quaternary Science Reviews'
- doi `10.5334/bha.22111`: different work: Crossref 'Editorial' in 'Bulletin of the History of Archaeology'
- archive_url `https://archive.org/details/travelsincentral01mouhuoft`: 404
- archive_url `https://archive.org/details/angkorintroducti0000coed`: 404
- archive_url `https://archive.org/details/brothernumberone00chan`: 404

### `apartheid`

- archive_url `https://archive.org/details/longwalktofre00mand`: 404
- archive_url `https://archive.org/details/iwritewhatilike0000biko`: 404
- archive_url `https://archive.org/details/nofuturewithou00tutu`: 404

### `apollo-11-moon-landing`

- archive_url `https://archive.org/details/challengetoapoll0000sidd`: 404
- archive_url `https://archive.org/details/korolevhowonemna0000harf`: 404
- archive_url `https://archive.org/details/digitalapollohum0000mind`: 404

### `arab-spring`

- doi `10.1515/9780804799027`: 404
- doi `10.1017/S0020743812000761`: different work: Crossref 'MES volume 44 issue 3 Cover and Front matter' in 'International Journal of Middle East Studies'
- doi `10.1353/jod.2016.0067`: different work: Crossref 'Iraq’s Year of Rage' in 'Journal of Democracy'
- doi `10.1017/S0020743814000853`: different work: Crossref 'James G. Blight, Janet M. Lang, Hussein Banai, Malcolm Byrne, and John Tirman, Becoming Enemies: US to ' in 'International Journal of Middle East Studies'
- doi `10.1353/jod.2017.0010`: different work: Crossref 'The Never-Boring Balkans: The Elections of 2016' in 'Journal of Democracy'
- doi `10.1093/acprof:oso/9780199314058.001.0001`: 404
- doi `10.1515/9781400848577`: different work: Crossref 'Jews and the Military' in ''
- doi `10.1353/jod.2016.0067`: different work: Crossref 'Iraq’s Year of Rage' in 'Journal of Democracy'
- doi `10.1017/S0020818313000459`: 404
- doi `10.1093/acprof:oso/9780190462475.001.0001`: 404
- doi `10.1177/0888325413496814`: 404
- doi `10.2307/j.ctt1np6dm`: 404

### `armenian-genocide`

- doi `10.1111/j.1469-8129.2006.00266_7.x`: different work (manual)
- doi `10.12987/yale/9780300186963.001.0001`: 404

### `ashoka-maurya-empire`

- doi `10.2307/3035135`: different work: Crossref 'The Edicts of Asoka' in 'Pacific Affairs'
- doi `10.1093/acprof:oso/9780195643367.001.0001`: 404
- archive_url `https://archive.org/details/historyofsouthin0000kani`: 404

### `bolivarian-revolutions`

- doi `10.2307/20050198`: different work (manual)
- doi `10.2307/2677551`: different work (manual)
- doi `10.1163/2468-1733_shafr_sim020150038`: different work (manual)
- doi `10.1093/acprof:oso/9780190459840.003.0002`: different work (manual)
- doi `10.4159/harvard.9780674726116`: different work: Crossref 'The Falling Sky' in ''
- archive_url `https://archive.org/details/oppressedbutnot0000rive`: 404

### `cambodian-genocide`

- doi `10.1017/9781780687094`: different work: Crossref 'The Killing of Death' in ''
- doi `10.2307/2759949`: a review, not the work: Crossref author labrecque in 'Pacific Affairs'
- doi `10.5860/choice.43-2697`: different work: Crossref 'Afrique sur Seine: a new generation of African writers in Paris' in 'Choice Reviews Online'
- archive_url `https://archive.org/details/brotherenemywar000chan`: 404

### `congo-free-state`

- doi `10.14375/np.9782871066514`: different work: Crossref 'Histoire du Congo' in ''
- doi `10.5860/choice.40-5625`: different work: Crossref 'Gendering talk' in 'Choice Reviews Online'
- archive_url `https://archive.org/details/congofromleopold0000nzon`: 404
- archive_url `https://archive.org/details/blacklivingstons0000kenn`: 404

### `congo-wars`

- archive_url `https://archive.org/details/wewishtoinforyou00gour`: 404
- archive_url `https://archive.org/details/congofromleopold0000nzon`: 404

### `creation-of-israel-nakba`

- doi `10.1525/jps.2006.36.1.6`: a review, not the work: Crossref author papp in 'Journal of Palestine Studies'
- doi `10.7312/shla93334`: 404
- doi `10.1093/ia/iim023`: 404
- archive_url `https://archive.org/details/soldierwithara00glub`: 404

### `cuban-revolution`

- archive_url `https://archive.org/details/healingmassescub0000fein`: 404

### `cyrus-cylinder`

- doi `10.5860/choice.40-5765`: different work: Crossref 'True religion' in 'Choice Reviews Online'
- doi `10.2307/3642581`: different work: Crossref 'Some New Assyrian Rock-Reliefs in Turkey' in 'Anatolian Studies'
- doi `10.1163/15685209-12341284`: different work: Crossref 'Anne-Marie EDDÉ, Saladin. Translated by Jane Marie Todd. Cambridge and London: The Belknap Press of ' in 'Journal of the Economic and Social History of the Orient'
- doi `10.1017/CHOL9780521780858.007`: 404
- doi `10.12987/yale/9780300043143.001.0001`: 404
- doi `10.1515/9781400831708`: different work: Crossref 'The Geographic Spread of Infectious Diseases: Models and Applications' in ''
- doi `10.7208/chicago/9780226729480.001.0001`: 404
- archive_url `https://archive.org/details/asshurandthelan00rassgoog`: 404

### `fall-of-berlin-wall`

- doi `10.1093/ia/iiac089`: a review, not the work: Crossref author papageorgiou in 'International Affairs'
- doi `10.2307/20455169`: different work: Crossref 'Cross-Dress for Success: Performing Ivan Heng and Chowee Leow\'s "An Occasional Orchid" and Stella Ko' in "Tulsa Studies in Women's Literature"
- doi `10.1023/B:Dam.0000009338.23400.3d`: 404
- doi `10.2307/20045108`: different work: Crossref 'Order and Disorder in the New World' in 'Foreign Affairs'
- archive_url `https://archive.org/details/darkernationspe000pras`: 404

### `fall-of-constantinople`

- doi `10.2307/2495267`: different work: Crossref 'Social Structure and National Movements among the Yugoslav Peoples on the Eve of the First World War' in 'Slavic Review'
- archive_url `https://archive.org/details/tarikhi-ebul-feth`: 404
- archive_url `https://archive.org/details/mehmedconquerorh0000babi`: 404
- archive_url `https://archive.org/details/diary-of-siege-of-constantinople`: 404
- archive_url `https://archive.org/details/byzantiumdecline0000norw`: 404
- archive_url `https://archive.org/details/balkans1804199900glen`: 404
- archive_url `https://archive.org/details/latinslevant00mill`: 404

### `fall-of-rome`

- doi `10.1525/9780520957756`: 404
- archive_url `https://archive.org/details/augustineofhippo0000brow`: 404

### `french-revolution`

- doi `10.2307/3185360`: different work: Crossref 'The Real Clarence Thomas: Confirmation Veracity Meets Performance Reality' in 'The American Journal of Legal History'
- doi `10.5149/9780807861592_dubois`: 404
- archive_url `https://archive.org/details/blackjacobinstou0000jame_h9v8`: 404

### `global-financial-crisis-2008`

- archive_url `https://archive.org/details/toobigtofailhows0000sork`: 404
- archive_url `https://archive.org/details/bailoutinsideacc0000baro`: 404
- archive_url `https://archive.org/details/democracyproject0000grae`: 404
- archive_url `https://archive.org/details/thistimeisdiffer0000rein`: 404
- archive_url `https://archive.org/details/globalizationpar0000rodr`: 404
- archive_url `https://archive.org/details/gettingofftrackh0000tayl`: 404

### `great-depression`

- archive_url `https://archive.org/details/sinceyesterday0000alle`: 404
- archive_url `https://archive.org/details/latinamericain1900thor`: 404
- archive_url `https://archive.org/details/goldenfettersgol0000eich`: 404

### `great-leap-forward`

- archive_url `https://archive.org/details/maosgreatfaminehi0000diko`: 404

### `haitian-revolution`

- doi `10.1093/nq/s7-ii.32.108g`: different work (manual)
- doi `10.4324/9781315840376-8`: different work (manual)
- doi `10.5860/choice.49-3633`: different work (manual)

### `hiroshima-nagasaki`

- doi `10.1080/02690055.2020.1721019`: different work (manual)
- doi `10.1215/9780822376699`: different work: Crossref 'The First Anglo-Afghan Wars' in ''
- doi `10.2307/2659211`: 404
- doi `10.9783/9780812292312`: different work: Crossref 'Other Middle Ages' in ''

### `holodomor`

- doi `10.2307/2750764`: a review, not the work: Crossref author barnes in 'Pacific Affairs'
- doi `10.1057/9780230523753`: different work: Crossref 'Democracy and Civil Society in Asia' in ''
- doi `10.1093/hwj/dbp013`: different work: Crossref 'Mac Paps' in 'History Workshop Journal'
- archive_url `https://archive.org/details/harvestofsorrow00conq`: 404

### `industrial-revolution`

- doi `10.1017/CBO9781139627016`: 404
- doi `10.1080/13563467.2017.1348372`: 404
- doi `10.1080/03066150.2016.1235036`: different work (manual)
- doi `10.7312/columbia/9780231187312.003.0013`: 404
- archive_url `https://archive.org/details/villagelabourers00hammuoft`: 404
- archive_url `https://archive.org/details/townlabourer176000hamm`: 404
- archive_url `https://archive.org/details/empireofcottongo0000beck`: 404
- archive_url `https://archive.org/details/capitalismandsla0000will`: 404
- archive_url `https://archive.org/details/povertyunbritish00naorrich`: 404
- archive_url `https://archive.org/details/empireofcottongo0000beck`: 404
- archive_url `https://archive.org/details/considerationson00bolt`: 404

### `korean-war`

- doi `10.9783/9780812292312`: different work: Crossref 'Other Middle Ages' in ''
- doi `10.9783/9780812292312`: different work: Crossref 'Other Middle Ages' in ''
- archive_url `https://archive.org/details/koreanwarhistory00cumi`: 404
- archive_url `https://archive.org/details/thiskindofwar00fehr`: 404
- archive_url `https://archive.org/details/koreanwarhistory00cumi`: 404
- archive_url `https://archive.org/details/bridgeatnogunrih0000hanl`: 404

### `meiji-restoration`

- doi `10.18574/9781479899852`: 404
- doi `10.2307/4127210`: a review, not the work: Crossref author benari in 'Pacific Affairs'
- doi `10.21313/hawaii/9780824828165.001.0001`: 404
- doi `10.7312/yosh13532`: 404

### `mongol-conquest-baghdad`

- doi `10.2307/1845462`: different work: Crossref 'The History of the World-Conqueror' in 'The American Historical Review'
- doi `10.1515/9781400847334`: different work: Crossref 'Climate Dynamics' in ''
- doi `10.12987/yale/9780300159110.001.0001`: 404
- archive_url `https://archive.org/details/TheMuslimHistorianIbnKhaldun`: 404

### `mongol-empire`

- archive_url `https://archive.org/details/genghiskhanmakin00weat`: 404
- archive_url `https://archive.org/details/dailylifeinchin000gern`: 404
- archive_url `https://archive.org/details/travelstravelsof00polo`: 404
- archive_url `https://archive.org/details/historyofworldco01juvauoft`: 404
- archive_url `https://archive.org/details/mongolsrussia0000vern`: 404
- archive_url `https://archive.org/details/genghiskhanmakin00weat`: 404

### `mughal-empire`

- doi `10.1017/CHOL9780521251198`: 404
- doi `10.1093/acprof:oso/9780198077244.003.0035`: 404
- doi `10.1017/9781316414392`: 404
- doi `10.1017/S0021911800009724`: 404
- archive_url `https://archive.org/details/bababornamefirdo00babuuoft`: 404
- archive_url `https://archive.org/details/akbarnama01abufuoft`: 404
- archive_url `https://archive.org/details/hindutva-vinayak-damodar-savarkar`: 404
- archive_url `https://archive.org/details/historyofindia0002spea`: 404
- archive_url `https://archive.org/details/embassyofsirthom01roet`: 404
- archive_url `https://archive.org/details/elementaryaspect0000guha`: 404
- archive_url `https://archive.org/details/SirrIAkbar`: 404

### `opium-wars`

- doi `10.2307/2761148`: a review, not the work: Crossref author howard in 'Pacific Affairs'
- doi `10.1017/S0026749X07003356`: different work (manual)
- doi `10.1163/9789004390508`: different work: Crossref 'The Shroud at Court' in ''

### `ottoman-empire`

- archive_url `https://archive.org/details/speechdeliveredg00atat`: 404
- archive_url `https://archive.org/details/arabawakening00anto`: 404
- archive_url `https://archive.org/details/bulgarianhorrors00gladuoft`: 404
- archive_url `https://archive.org/details/balkans1804199900glen`: 404
- archive_url `https://archive.org/details/medjelle00turkuoft`: 404

### `partition-of-india`

- doi `10.2307/2756705`: a review, not the work: Crossref author moulton in 'Pacific Affairs'
- doi `10.2307/2756706`: different work: Crossref 'The Transfer of Power, 1942-7. Constitutional Relations between Britain and India. Volume V: The Sim' in 'Pacific Affairs'
- doi `10.2307/2758176`: a review, not the work: Crossref author qureshi in 'Pacific Affairs'
- doi `10.4324/9780321377548`: 404

### `peloponnesian-war`

- doi `10.1093/acprof:oso/9780198142348.001.0001`: 404
- doi `10.5040/9781472511539`: 404

### `scramble-for-africa`

- doi `10.3368/gs.3.1.111`: different work (manual)
- archive_url `https://archive.org/details/mahdiststateInsu0000holt`: 404
- archive_url `https://archive.org/details/sanusiofcyrenaica0000evan`: 404

### `silk-road`

- archive_url `https://archive.org/details/religionsofsil00folt`: 404
- archive_url `https://archive.org/details/mediterraneansoc0006goit`: 404
- archive_url `https://archive.org/details/plaguespeople00mcne`: 404

### `six-day-war`

- doi `10.1093/oso/9780195151749.001.0001`: 404
- doi `10.2307/j.ctvc775xx`: 404
- doi `10.3751/60.2.14`: 404
- archive_url `https://archive.org/details/abbaeban00abba`: 404
- archive_url `https://archive.org/details/cairodocumentsin0000heik`: 404
- archive_url `https://archive.org/details/palestinenakbade0000masa`: 404

### `spanish-flu-1918`

- archive_url `https://archive.org/details/greatinfluenzast0000barr`: 404

### `sykes-picot-agreement`

- archive_url `https://archive.org/details/lineinsandbritai0000barr`: 404
- archive_url `https://archive.org/details/modernhistoryofk0000mcdo`: 404

### `the-crusades`

- doi `10.1177/096834450100800206`: different work (manual)
- archive_url `https://archive.org/details/jewsandcrusaders00eide`: 404
- archive_url `https://archive.org/details/itineraryofbenja00benj`: 404

### `tiananmen-square`

- doi `10.2307/2169643`: different work (manual)
- doi `10.1007/978-1-349-27441-3_9`: different work: Crossref 'China into the Twenty-First Century' in 'Contemporary China'
- doi `10.2307/2760686`: a review, not the work: Crossref author saich in 'Pacific Affairs'
- doi `10.1017/S0004972100048528`: 404

### `trail-of-tears`

- doi `10.1007/978-3-319-51902-9_4`: different work (manual)
- doi `10.1353/jowh.2010.0030`: different work (manual)
- doi `10.36019/9780813550336-009`: different work (manual)
- doi `10.1353/rah.2006.0088`: 404
- archive_url `https://archive.org/details/riseofamericande00wile`: 404

### `transatlantic-slave-trade`

- doi `10.1093/acrefore/9780199366439.013.962`: different work (manual)
- doi `10.1017/CBO9781139170505`: different work: Crossref 'High Energy Astrophysics' in ''

### `treaty-of-waitangi`

- doi `10.2307/2760517`: a review, not the work: Crossref author fisher in 'Pacific Affairs'
- archive_url `https://archive.org/details/longwhitecloudao00reev`: 404

### `vietnam-war`

- archive_url `https://archive.org/details/vietnamnecessaryw0000lind`: 404
- archive_url `https://archive.org/details/bestbrightestdav00halb`: 404
- archive_url `https://archive.org/details/hochiminhlife0000duik`: 404
- archive_url `https://archive.org/details/sacredwillowfour0000duon`: 404
- archive_url `https://archive.org/details/inretrospecttra000mcna`: 404
- archive_url `https://archive.org/details/pentagonpapers00grav`: 404
- archive_url `https://archive.org/details/voicesfromplaino0000bran`: 404
- archive_url `https://archive.org/details/patriotsvietnamy0000appy`: 404
- archive_url `https://archive.org/details/vietnamwars19451900youn`: 404

### `womens-suffrage`

- archive_url `https://archive.org/details/suffragettehistor00pank`: 404
- archive_url `https://archive.org/details/socialbasisofwom00koll`: 404

## Left in place, unresolved

These DOIs resolve to JSTOR or a publisher page behind a bot challenge, and Crossref holds no record, so nothing could be read either way. They are not known to be wrong and stay until the ledger rebuild reads them: `10.2307/484058` (congo-free-state, Louis and Stengers), `10.2307/2535556` (creation-of-israel-nakba, Said), `10.2307/2171327` (fall-of-berlin-wall, Zelikow and Rice), `10.2307/4612165` (french-revolution, Schama), `10.2307/1850620` (mali-empire-mansa-musa, Levtzion), `10.2307/20050025` (partition-of-india, Butalia), `10.2307/27650162` (trail-of-tears, Warshauer), `10.1080/2201473x.2012.10648834` (trail-of-tears, Wolfe).

## The check

`tests/test_history_data.py` now fails if any History media item is an Unsplash or Pexels item, and if an entry marked `verified: false` still carries a `doi`, `archive_url` or `url`.
