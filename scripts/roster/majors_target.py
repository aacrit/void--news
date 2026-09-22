#!/usr/bin/env python3
"""Target list of major outlets by region, built on PER-MARKET BALANCE.

CEO direction 2026-09-22: make sure the major outlets across the globe are
covered, US and Europe especially, then India and South Asia and Asia, with
Africa and the Middle East targeted at the key ones.

WHY THE LIST IS SHAPED THIS WAY, and it is not prominence.

Measured on the 41-day archive: feed breakage does not thin markets evenly, it
TILTS them. Mean outlet baseline, whole roster against the healthy subset
(direct-fed, placed, publishing regularly):

    India          51.0 (n=40)  ->  63.6 (n=7)    +12.6 rightward
    Africa         43.8 (n=12)  ->  35.0 (n=1)     -8.8 leftward
    Middle East    47.4 (n=21)  ->  52.5 (n=6)     +5.1 rightward
    Germany        47.0 (n=10)  ->  50.0 (n=2)     +3.0
    Europe ex-UK   46.9 (n=48)  ->  44.0 (n=10)    -2.9
    US            51.1 (n=422)  ->  50.5 (n=82)    -0.7
    WHOLE ROSTER  50.2 (n=730)  ->  50.5 (n=148)   +0.4

The roster-wide figure is +0.4, which looks like balance and is not. When a
story is about India, the Bench currently shows a rightward spread that is an
artefact of which feeds happen to work. So the target for a market is not "its
most famous paper", it is AT LEAST ONE HEALTHY OUTLET ON EACH SIDE plus a
centre or wire anchor. A market covered from one side is worse than a market
not covered, because the one-sided version publishes a lean and looks measured.

Measured today, Europe: 25 of 34 markets have NO healthy source at all, only
the UK has both wings healthy, France and Spain and the Netherlands and Ukraine
are covered from the LEFT only, Turkey from the RIGHT only, and Germany, Italy
and Ireland are centre only.

THIS LIST IS EDITORIAL JUDGEMENT, NOT MEASUREMENT. The lean tags below are the
author's reading of each outlet's editorial position, offered so the BALANCE of
the list can be argued with rather than just its membership. They are targets
for the roster's own placement process, not placements themselves: an outlet
that gets added still goes through credibility vetting and gets its baseline
set the normal way. Nothing in the pipeline reads this file.

Format: market -> list of (outlet, intended_side) where side is L, C or R.
"""

# L = left of centre in its own market, C = centre or wire, R = right of centre.
# Sides are relative to the market, not to US politics.
MAJORS = {
 # ---- US and UK: both already have healthy wings; listed for completeness ----
 "US": [("The New York Times","L"),("The Washington Post","L"),("CNN","L"),
        ("MSNBC","L"),("NPR","L"),("HuffPost","L"),("Vox","L"),("ProPublica","L"),
        ("Associated Press","C"),("Reuters","C"),("USA Today","C"),("Axios","C"),
        ("Bloomberg","C"),("Politico","C"),("The Wall Street Journal","R"),
        ("Fox News","R"),("National Review","R"),("The Washington Times","R"),
        ("New York Post","R"),("The Dispatch","R")],
 "UK": [("The Guardian","L"),("The Mirror","L"),("The Independent","L"),
        ("The Observer","L"),("New Statesman","L"),("BBC News","C"),
        ("Financial Times","C"),("Sky News","C"),("The Economist","C"),
        ("The Times","R"),("The Daily Telegraph","R"),("Daily Mail","R"),
        ("The Spectator","R"),("The Sun","R")],
 "Ireland": [("The Irish Times","C"),("Irish Independent","R"),("RTE News","C"),
        ("The Journal.ie","L")],

 # ---- Europe: the region the CEO named, and the weakest. One per side. ----
 "France": [("Le Monde","L"),("Liberation","L"),("Mediapart","L"),
        ("France 24","C"),("RFI","C"),("Les Echos","C"),
        ("Le Figaro","R"),("L'Express","R"),("Le Point","R")],
 "Germany": [("Sueddeutsche Zeitung","L"),("Der Spiegel","L"),("Die Zeit","L"),("taz","L"),
        ("Deutsche Welle","C"),("Frankfurter Allgemeine","R"),("Die Welt","R"),
        ("Handelsblatt","C"),("Focus","R")],
 "Italy": [("la Repubblica","L"),("Il Fatto Quotidiano","L"),
        ("Corriere della Sera","C"),("ANSA","C"),
        ("Il Giornale","R"),("Il Foglio","R"),("Libero","R")],
 "Spain": [("El Pais","L"),("eldiario.es","L"),("Publico","L"),
        ("El Mundo","R"),("ABC","R"),("La Razon","R"),("La Vanguardia","C")],
 "Netherlands": [("De Volkskrant","L"),("NRC","C"),("Trouw","L"),
        ("De Telegraaf","R"),("Elsevier Weekblad","R"),("DutchNews.nl","C")],
 "Belgium": [("De Standaard","C"),("Le Soir","L"),("De Morgen","L"),
        ("La Libre Belgique","R"),("The Brussels Times","C")],
 "Nordics": [("Dagens Nyheter","L"),("Svenska Dagbladet","R"),("Aftonbladet","L"),
        ("Aftenposten","R"),("Politiken","L"),("Jyllands-Posten","R"),
        ("Helsingin Sanomat","C"),("Iceland Review","C")],
 "Central Europe": [("Gazeta Wyborcza","L"),("Rzeczpospolita","R"),("Notes from Poland","C"),
        ("Hospodarske noviny","C"),("Telex","L"),("Magyar Nemzet","R"),
        ("Denik N","C"),("Balkan Insight","C")],
 "Southern Europe": [("Kathimerini","R"),("Ekathimerini","C"),("Publico (Portugal)","L"),
        ("Expresso","C"),("Diario de Noticias","C")],
 "Switzerland/Austria": [("Neue Zurcher Zeitung","R"),("Tages-Anzeiger","L"),
        ("SWI Swissinfo.ch","C"),("Der Standard","L"),("Die Presse","R")],
 "Ukraine/Russia": [("Kyiv Independent","C"),("Ukrainska Pravda","C"),("Kyiv Post","C"),
        ("Novaya Gazeta Europe","L"),("The Moscow Times","L"),("Meduza","L")],
 "Turkey": [("Hurriyet Daily News","C"),("Daily Sabah","R"),("Anadolu Agency","R"),
        ("Duvar English","L"),("Bianet","L")],
 "EU-wide": [("Politico Europe","C"),("Euronews","C"),("Euractiv","C"),("EUobserver","C")],

 # ---- India and South Asia: fully on the roster, almost entirely broken ----
 "India": [("The Hindu","L"),("Scroll.in","L"),("The Wire","L"),("The Telegraph India","L"),
        ("NDTV","C"),("The Indian Express","C"),("The Times of India","C"),
        ("The Print","C"),("Hindustan Times","C"),("The Economic Times","C"),
        ("Republic World","R"),("OpIndia","R"),("Firstpost","R"),("India Today","C"),
        ("Swarajya","R"),("The New Indian Express","R")],
 "Pakistan/Bangladesh/Sri Lanka/Nepal": [("Dawn","L"),("The Express Tribune","C"),
        ("The News International","R"),("Geo News","C"),
        ("The Daily Star (Bangladesh)","L"),("Prothom Alo","C"),("Dhaka Tribune","C"),
        ("Daily Mirror (Sri Lanka)","C"),("The Island (Sri Lanka)","R"),
        ("The Kathmandu Post","C")],

 # ---- East and Southeast Asia ----
 "East Asia": [("South China Morning Post","C"),("Nikkei Asia","C"),("The Japan Times","C"),
        ("Asahi Shimbun","L"),("Yomiuri Shimbun","R"),("Kyodo News","C"),
        ("The Korea Herald","C"),("Hankyoreh","L"),("Chosun Ilbo","R"),
        ("Yonhap News Agency","C"),("Taipei Times","L"),("Focus Taiwan","C"),
        ("Xinhua","R"),("Global Times","R"),("Caixin","C"),("Hong Kong Free Press","L")],
 "Southeast Asia": [("The Straits Times","C"),("Channel NewsAsia","C"),("Bangkok Post","C"),
        ("The Jakarta Post","L"),("Tempo","L"),("Philippine Daily Inquirer","C"),
        ("Rappler","L"),("The Manila Times","R"),("Malay Mail","C"),("Bernama","C"),
        ("VnExpress","C")],

 # ---- Middle East: currently +5.1 rightward once breakage is applied ----
 "Middle East": [("Haaretz","L"),("The Times of Israel","C"),("The Jerusalem Post","R"),
        ("i24NEWS","C"),("Al Jazeera","L"),("Al Arabiya","R"),("Arab News","R"),
        ("The National (UAE)","C"),("Gulf News","C"),("Middle East Eye","L"),
        ("Al-Monitor","C"),("The Daily Star (Lebanon)","C"),("L'Orient Today","C"),
        ("Tehran Times","R"),("Iran International","L")],

 # ---- Africa: only ONE healthy source today, and an 8.8 point leftward tilt ----
 "Africa": [("Mail & Guardian","L"),("Daily Maverick","L"),("News24","C"),
        ("BusinessDay (SA)","R"),("IOL","C"),
        ("Premium Times","L"),("The Punch","C"),("Vanguard","C"),("TheCable","L"),
        ("Daily Trust","R"),
        ("Daily Nation","C"),("The Standard (Kenya)","C"),("The EastAfrican","C"),
        ("Ahram Online","R"),("Mada Masr","L"),
        ("GhanaWeb","C"),("Ghana News Agency","C"),("The Africa Report","C"),
        ("AllAfrica","C"),("Addis Standard","C")],

 # ---- Americas outside the US: Brazil and Mexico effectively uncovered ----
 "Canada": [("The Globe and Mail","C"),("CBC News","L"),("Toronto Star","L"),
        ("National Post","R"),("CTV News","C")],
 "Latin America": [("Folha de S.Paulo","C"),("O Globo","R"),("Brazilian Report","C"),
        ("Clarin","R"),("La Nacion (AR)","R"),("Pagina 12","L"),("Buenos Aires Times","C"),
        ("Reforma","C"),("El Universal (MX)","C"),("La Jornada","L"),
        ("El Comercio","R"),("La Tercera","R"),("El Mostrador","L"),
        ("El Tiempo","C"),("MercoPress","C")],

 # ---- Oceania ----
 "Oceania": [("The Sydney Morning Herald","L"),("The Age","L"),("ABC News (Australia)","C"),
        ("The Guardian Australia","L"),("The Australian","R"),
        ("New Zealand Herald","C"),("RNZ","C"),("Stuff","C")],
}


def flat():
    """(market, outlet, side) for every entry."""
    return [(m, o, s) for m, lst in MAJORS.items() for o, s in lst]


if __name__ == "__main__":
    import collections
    rows = flat()
    print(f"markets: {len(MAJORS)}, target outlets: {len(rows)}")
    sides = collections.Counter(s for _, _, s in rows)
    print("intended sides:", dict(sides))
    print("\nper-market balance of the TARGET list (L/C/R):")
    for m, lst in MAJORS.items():
        c = collections.Counter(s for _, s in lst)
        gap = [k for k in "LR" if c[k] == 0]
        flag = f"   <-- target list itself lacks {'/'.join(gap)}" if gap else ""
        print(f"  {m:36s} L{c['L']:>2} C{c['C']:>2} R{c['R']:>2}{flag}")
