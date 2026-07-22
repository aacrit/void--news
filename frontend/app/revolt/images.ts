/* ===========================================================================
   void --revolt — hero image override map.
   Real, working public-domain / free-licensed lead images (upload.wikimedia.org
   ORIGINALS, which never 404 on a thumb-width mismatch) harvested from Wikipedia.
   Used as the hero for cards + detail stages when a revolution has no explicit
   heroImage. One file, so images apply to both the mock and the DB-backed render
   without a re-load. Attribution is a light credit; deep-dives link fuller sources.
   =========================================================================== */

export interface RevoltHeroImage {
  url: string;
  attribution: string;
}

export const REVOLT_HERO_IMAGES: Record<string, RevoltHeroImage> = {
  'french-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/5/57/Anonymous_-_Prise_de_la_Bastille.jpg', attribution: 'Storming of the Bastille, anonymous, via Wikimedia Commons' },
  'russian-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/7/7c/%D0%9C%D0%B8%D1%82%D0%B8%D0%BD%D0%B3_%D0%BD%D0%B0_%D0%9D%D0%B5%D0%B2%D1%81%D0%BA%D0%BE%D0%BC_%D0%BF%D1%80%D0%BE%D1%81%D0%BF%D0%B5%D0%BA%D1%82%D0%B5_%281917%29.jpg', attribution: 'Petrograd, 1917, via Wikimedia Commons' },
  'iranian-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/4/4a/Mass_demonstration_in_Iran%2C_date_unknown.jpg', attribution: 'Mass demonstration, Iran 1979, via Wikimedia Commons' },
  'haitian-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/4/44/Incendie_de_la_Plaine_du_Cap._Massacre_des_Blancs_par_les_esclaves_noirs_r%C3%A9volt%C3%A9s._France_militaire._Martinet_et_Masson.jpg', attribution: 'Saint-Domingue uprising, via Wikimedia Commons' },
  'american-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/f/f9/Declaration_of_Independence_%281819%29%2C_by_John_Trumbull.jpg', attribution: 'Declaration of Independence, John Trumbull, via Wikimedia Commons' },
  'fall-of-communism-1989': { url: 'https://upload.wikimedia.org/wikipedia/commons/1/1c/West_and_East_Germans_at_the_Brandenburg_Gate_in_1989.jpg', attribution: 'Brandenburg Gate, 1989, via Wikimedia Commons' },
  'people-power-1986': { url: 'https://upload.wikimedia.org/wikipedia/en/3/3b/EDSA_Revolution_pic1.jpg', attribution: 'EDSA, 1986, via Wikimedia' },
  'arab-spring': { url: 'https://upload.wikimedia.org/wikipedia/commons/9/9e/Tunisian_Revolution_Protest.jpg', attribution: 'Tunisian Revolution, via Wikimedia Commons' },
  'glorious-revolution-1688': { url: 'https://upload.wikimedia.org/wikipedia/commons/e/e9/William_of_Orange_III_and_his_Dutch_army_land_in_Brixham%2C_1688.jpg', attribution: 'William of Orange lands at Brixham, 1688, via Wikimedia Commons' },
  'english-civil-war': { url: 'https://upload.wikimedia.org/wikipedia/commons/b/b3/Battle_of_Naseby%2C_hand-coloured_copper_engraving.jpg', attribution: 'Battle of Naseby, via Wikimedia Commons' },
  'springtime-of-nations-1848': { url: 'https://upload.wikimedia.org/wikipedia/commons/c/cd/Horace_Vernet-Barricade_rue_Soufflot.jpg', attribution: 'Barricade, rue Soufflot, Horace Vernet, via Wikimedia Commons' },
  'meiji-restoration': { url: 'https://upload.wikimedia.org/wikipedia/commons/d/de/Emperor_Meiji_by_Takahashi_Yuichi.jpg', attribution: 'Emperor Meiji, Takahashi Yuichi, via Wikimedia Commons' },
  'mexican-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/6/6e/Decena_tr%C3%A1gica.JPG', attribution: 'Mexican Revolution, via Wikimedia Commons' },
  'chinese-revolution-1949': { url: 'https://upload.wikimedia.org/wikipedia/commons/5/52/Communists_Being_Arrested_in_the_Shanghai_Massacre.jpg', attribution: 'Chinese Revolution, via Wikimedia Commons' },
  'chinese-cultural-revolution': { url: 'https://upload.wikimedia.org/wikipedia/en/c/c6/Cultural_Revolution_poster.jpg', attribution: 'Cultural Revolution poster, via Wikimedia' },
  'cuban-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/5/5d/Fidel_Castro_and_his_men_in_the_Sierra_Maestra.jpg', attribution: 'Sierra Maestra, via Wikimedia Commons' },
  'algerian-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/0/0f/National_Liberation_Army_Soldiers_%287%29.jpg', attribution: 'FLN soldiers, via Wikimedia Commons' },
  'carnation-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/f/f7/Revolu%C3%A7%C3%A3o_dos_Cravos.jpg', attribution: 'Carnation Revolution, via Wikimedia Commons' },
  'sandinista-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/7/77/Revoluci%C3%B3n_sandinista.png', attribution: 'Sandinista Revolution, via Wikimedia Commons' },
  'anti-apartheid': { url: 'https://upload.wikimedia.org/wikipedia/commons/7/75/Mandela_burn_pass_1960.jpg', attribution: 'Mandela burning his passbook, 1960, via Wikimedia Commons' },
  'euromaidan': { url: 'https://upload.wikimedia.org/wikipedia/commons/5/53/Euromaidan_collage.jpg', attribution: 'Euromaidan, via Wikimedia Commons' },
  'latin-american-independence': { url: 'https://upload.wikimedia.org/wikipedia/commons/e/e5/Congreso_de_C%C3%BAcuta.jpg', attribution: 'Congress of Cucuta, via Wikimedia Commons' },
  'myanmar-spring-revolution': { url: 'https://upload.wikimedia.org/wikipedia/en/c/c5/2021_Myanmar_coup.jpg', attribution: '2021 Myanmar protests, via Wikimedia' },
  'iran-woman-life-freedom': { url: 'https://upload.wikimedia.org/wikipedia/commons/b/b9/Amir_Kabir_University_uprising_September_2022_%283%29.jpg', attribution: 'Amir Kabir University, September 2022, via Wikimedia Commons' },
  'sudan-civil-war': { url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/War_in_Sudan_%282023%29.svg/960px-War_in_Sudan_%282023%29.svg.png', attribution: 'War in Sudan control map, via Wikimedia Commons' },
  'venezuela': { url: 'https://upload.wikimedia.org/wikipedia/commons/0/03/Venezuelan_Assembly_special_session_01.jpg', attribution: 'Venezuelan National Assembly, via Wikimedia Commons' },
  'bangladesh-july-revolution': { url: 'https://upload.wikimedia.org/wikipedia/commons/c/cc/7.Bangladesh_quota_reform_movement_2024.jpg', attribution: 'Bangladesh, 2024, via Wikimedia Commons' },
  'syria-post-assad': { url: 'https://upload.wikimedia.org/wikipedia/commons/c/cd/Syrians_celebrate_the_fall_of_Assad_at_the_Umayyad_mosque%2C_14_December_2024.jpg', attribution: 'Damascus, 14 December 2024, via Wikimedia Commons' },
  'georgia-eu-protests': { url: 'https://upload.wikimedia.org/wikipedia/commons/b/b7/Tbilisi_-_election_protests_28_October_2024.jpg', attribution: 'Tbilisi, October 2024, via Wikimedia Commons' },
  'belarus-2020': { url: 'https://upload.wikimedia.org/wikipedia/commons/5/54/Protest_actions_in_Minsk_%28Belarus%29_near_Stella%2C_August_16.jpg', attribution: 'Minsk, August 2020, via Wikimedia Commons' },
  'kenya-gen-z': { url: 'https://upload.wikimedia.org/wikipedia/commons/8/81/Kenya_2024_protests_%2821%29.jpg', attribution: 'Nairobi, 2024, via Wikimedia Commons' },
  'hong-kong': { url: 'https://upload.wikimedia.org/wikipedia/commons/f/fb/Hong_Kong_anti-extradition_bill_protest_%2848108527758%29.jpg', attribution: 'Hong Kong, 2019, via Wikimedia Commons' },
  'cuba-2021': { url: 'https://upload.wikimedia.org/wikipedia/commons/f/f8/2021_Cuban_protests.png', attribution: '2021 Cuban protests, via Wikimedia Commons' },
  'thailand': { url: 'https://upload.wikimedia.org/wikipedia/commons/b/bf/Protest_in_2020_Democracy_Monument_%28I%29.jpg', attribution: 'Bangkok, 2020, via Wikimedia Commons' },
};

export function heroImageFor(slug: string): string | undefined {
  return REVOLT_HERO_IMAGES[slug]?.url;
}

export function heroAttributionFor(slug: string): string | undefined {
  return REVOLT_HERO_IMAGES[slug]?.attribution;
}
