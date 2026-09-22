#!/usr/bin/env python3
"""Target list of major outlets by region, for roster coverage audit.

CEO direction 2026-09-22: make sure the major outlets across the globe are
covered, US and Europe especially, then India/South Asia and Asia, with Africa
and the Middle East targeted at the key ones.

THIS LIST IS EDITORIAL JUDGEMENT, NOT MEASUREMENT. The criterion applied is
national reach or agenda-setting influence in the outlet's own market, with an
English-language edition available. It is offered for CEO review and should be
edited rather than treated as settled. Nothing in the pipeline reads it; it
exists so coverage can be audited against a stated standard instead of a
feeling.

KNOWN LIMITATION: matching against data/sources.json is fuzzy and produces
false positives on shared mastheads. Measured in the first run: the UK Daily
Telegraph matched the Australian one, The Observer matched The Observer Uganda,
India's The Wire matched The Wire China, and "The Daily Star" is both a
Bangladeshi and a Lebanese title. So the true absent count is HIGHER than the
28 the first audit reported. Treat a match as a candidate, not a fact.
"""

MAJORS = {
 "US": ["The New York Times","The Washington Post","The Wall Street Journal","USA Today",
        "Associated Press","Reuters","CNN","Fox News","NBC News","CBS News","ABC News",
        "NPR","Politico","Axios","The Atlantic","Bloomberg","MSNBC","Newsweek","Time",
        "The Hill","National Review","Breitbart","HuffPost","Vox","ProPublica","Los Angeles Times"],
 "UK/IE": ["BBC News","The Guardian","The Times","The Daily Telegraph","Financial Times",
        "The Independent","Daily Mail","The Sun","The Economist","Sky News","The Mirror",
        "The Observer","New Statesman","The Spectator","Channel 4 News","The Irish Times","RTE News"],
 "Europe": ["Deutsche Welle","Der Spiegel","Die Zeit","Frankfurter Allgemeine","Süddeutsche Zeitung",
        "Le Monde","Le Figaro","Liberation","France 24","RFI","El Pais","El Mundo",
        "Corriere della Sera","La Repubblica","ANSA","NRC","De Volkskrant","Politico Europe",
        "Euronews","Swissinfo","Dagens Nyheter","Aftenposten","Helsingin Sanomat",
        "Gazeta Wyborcza","Kyiv Independent","Ukrainska Pravda","Novaya Gazeta"],
 "India/South Asia": ["The Times of India","The Hindu","Hindustan Times","Indian Express",
        "The Economic Times","India Today","NDTV","The Print","Scroll.in","The Wire",
        "Dawn","The Express Tribune","Geo News","The Daily Star","Prothom Alo",
        "The Kathmandu Post","Daily Mirror (Sri Lanka)","The Island"],
 "East/SE Asia": ["South China Morning Post","Nikkei Asia","The Japan Times","Asahi Shimbun",
        "Yomiuri Shimbun","Kyodo News","The Korea Herald","Yonhap News Agency","The Straits Times",
        "Channel NewsAsia","Bangkok Post","The Jakarta Post","Philippine Daily Inquirer",
        "Rappler","Taipei Times","Focus Taiwan","Xinhua","Global Times","Caixin"],
 "Middle East": ["Al Jazeera","Al Arabiya","The National","Arab News","Haaretz",
        "The Times of Israel","The Jerusalem Post","Middle East Eye","Al-Monitor",
        "Anadolu Agency","Hürriyet Daily News","Tehran Times","Gulf News","The Daily Star (Lebanon)"],
 "Africa": ["Mail & Guardian","News24","Daily Maverick","BusinessDay","The Citizen",
        "Premium Times","The Punch","Vanguard","Daily Nation","The Standard",
        "The EastAfrican","Ahram Online","Egypt Independent","Ghana News Agency",
        "The Africa Report","AllAfrica","TheCable"],
 "Americas (non-US)": ["The Globe and Mail","CBC News","Toronto Star","National Post",
        "Folha de S.Paulo","O Globo","La Nacion","Clarin","El Universal","Reforma",
        "El Comercio","La Tercera","Buenos Aires Times","MercoPress"],
 "Oceania": ["The Sydney Morning Herald","The Australian","ABC News (Australia)",
        "The Age","The Guardian Australia","New Zealand Herald","RNZ","Stuff"],
}
