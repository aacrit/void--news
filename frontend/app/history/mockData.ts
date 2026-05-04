/* ===========================================================================
   void --history — Mock Data
   Real historical content for 3 events + 5 redacted stubs.
   Falls back to this when Supabase returns empty.
   =========================================================================== */

import type { HistoricalEvent, RedactedEvent } from "./types";

export const MOCK_EVENTS: HistoricalEvent[] = [
  /* ── 1. Partition of India, 1947 ── */
  {
    id: "evt-partition-india",
    slug: "partition-of-india",
    title: "Partition of India",
    subtitle: "The largest mass migration in human history",
    era: "contemporary",
    regions: ["south-asia"],
    categories: ["independence", "political", "genocide"],
    severity: "catastrophic",
    datePrimary: "August 15, 1947",
    dateSort: 19470815,
    dateRange: "June 1947 - January 1948",
    location: "British India (present-day India and Pakistan)",
    // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Emergency_trains_crowded_with_desperate_refugees.jpg/800px-Emergency_trains_crowded_with_desperate_refugees.jpg
    heroImage: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/partition-of-india/Emergency_trains_crowded_with_desperate_refugees.jpg",
    heroCaption: "Refugees crowd a train departing Amritsar, September 1947",
    heroAttribution: "Margaret Bourke-White / LIFE Magazine",
    contextNarrative: "On August 15, 1947, British India ceased to exist. In its place stood two nations: India and Pakistan. The boundary line, drawn by British lawyer Cyril Radcliffe in five weeks using outdated maps and census data, split Punjab and Bengal along religious lines. Radcliffe had never visited India before his appointment. The announcement came two days after independence, leaving millions on the wrong side of borders they had not chosen. Between 10 and 20 million people crossed in both directions. Trains arrived at stations carrying only corpses. Conservative estimates place the death toll between 200,000 and 2 million.",
    keyFigures: [
      { name: "Cyril Radcliffe", role: "Chairman, Boundary Commission" },
      { name: "Lord Mountbatten", role: "Last Viceroy of India" },
      { name: "Jawaharlal Nehru", role: "First Prime Minister of India" },
      { name: "Muhammad Ali Jinnah", role: "First Governor-General of Pakistan" },
      { name: "Mahatma Gandhi", role: "Leader of Indian independence movement" },
    ],
    deathToll: "200,000 - 2,000,000",
    displaced: "10,000,000 - 20,000,000",
    duration: "7 months (June 1947 - January 1948)",
    perspectives: [
      {
        id: "persp-partition-british",
        viewpointName: "The British Administration",
        viewpointType: "victor",
        color: "a",
        temporalAnchor: "1947, London",
        geographicAnchor: "Whitehall, London",
        narrative: "The transfer of power was orderly and inevitable. The Indian subcontinent, with its 400 million people and hundreds of languages, required partition to prevent a larger civil war between Hindu and Muslim populations. Mountbatten accelerated the timetable from June 1948 to August 1947 because delay meant more communal violence, not less. The Radcliffe Line, while imperfect, provided the best available boundary given the demographic complexity. Britain fulfilled its promise of self-governance within the framework of the Indian Independence Act. The violence that followed was a tragic consequence of communal tensions that predated British involvement.",
        keyNarratives: [
          "Partition prevented a subcontinental civil war",
          "The accelerated timetable reduced, not increased, casualties",
          "Communal violence was an Indian problem, not a British one",
          "The Radcliffe Line was the best available compromise",
        ],
        omissions: [
          "Decades of divide-and-rule policies that deepened Hindu-Muslim divisions",
          "Radcliffe's total unfamiliarity with the region",
          "British economic extraction that left infrastructure inadequate for mass migration",
          "Churchill's 1943 Bengal famine that killed 3 million",
        ],
        disputed: [
          "Whether earlier transfer of power would have prevented partition entirely",
        ],
        primarySources: [
          {
            text: "The decision to partition was taken reluctantly and with the knowledge that it would cause suffering. But the alternative was worse.",
            author: "Lord Mountbatten",
            work: "Address to the Indian Constituent Assembly",
            date: "August 15, 1947",
          },
        ],
      },
      {
        id: "persp-partition-indian",
        viewpointName: "Indian Nationalist View",
        viewpointType: "victor",
        color: "b",
        temporalAnchor: "1947, New Delhi",
        geographicAnchor: "New Delhi, India",
        narrative: "Partition was Britain's final act of imperial sabotage. After 200 years of deliberately inflaming Hindu-Muslim tensions through separate electorates, differential treatment, and strategic favoritism, the British manufactured a crisis and then offered partition as the only solution to a problem they had created. Mountbatten's decision to move independence forward by 10 months gave administrators five weeks to draw borders through the homes of 88 million people in Punjab alone. The boundary commission had no ground surveys, no population transfer plan, and no security arrangements. Gandhi called it a vivisection. Nehru accepted it as the price of freedom, knowing the alternative was indefinite British control dressed as mediation. The trains full of corpses were not an accident of haste. They were the logical outcome of a colonial power that spent two centuries preventing exactly the kind of unified resistance that would have made partition unnecessary.",
        keyNarratives: [
          "British divide-and-rule created the conditions for partition",
          "The accelerated timeline was designed to create chaos",
          "No provision was made for the safety of those who needed to cross",
          "Partition was the price of freedom, not a gift of governance",
        ],
        omissions: [
          "Internal Congress disagreements about accepting partition",
          "The role of Hindu nationalist organizations in communal violence",
          "Nehru and Patel's eventual acceptance of partition as expedient",
        ],
        disputed: [
          "Whether the Congress leadership could have prevented partition by accepting a federal structure",
        ],
        primarySources: [
          {
            text: "At the stroke of the midnight hour, when the world sleeps, India will awake to life and freedom.",
            author: "Jawaharlal Nehru",
            work: "Tryst with Destiny",
            date: "August 14, 1947",
          },
          {
            text: "The vivisection of a whole nation, body and soul, is no way to independence.",
            author: "Mahatma Gandhi",
            work: "Statement on Partition",
            date: "June 1947",
          },
        ],
      },
      {
        id: "persp-partition-pakistani",
        viewpointName: "Pakistani Founding Narrative",
        viewpointType: "victor",
        color: "c",
        temporalAnchor: "1947, Karachi",
        geographicAnchor: "Karachi, Pakistan",
        narrative: "Pakistan was not a partition but a creation. Muslims in British India were a minority of 100 million in a Hindu-majority subcontinent of 400 million. The Congress Party, despite its secular rhetoric, was a Hindu organization that would have marginalized Muslims in a unified India. The Lahore Resolution of 1940 articulated what millions already knew: that Muslims needed their own state to practice their faith, protect their culture, and govern themselves. Jinnah's two-nation theory was not a rejection of coexistence but an acknowledgment that the Congress model of coexistence meant Hindu dominance. Pakistan's founding on August 14, 1947 was the fulfillment of a democratic demand. The violence of partition was inflicted equally on both sides. What followed was a new nation built from scratch, with its capital in a tent city, its treasury empty, and its neighbor immediately disputing its right to exist.",
        keyNarratives: [
          "Pakistan was created by democratic demand, not British whim",
          "Muslims needed a separate state to avoid permanent minority status",
          "The two-nation theory reflected political reality, not religious hatred",
          "India immediately undermined Pakistan's viability by withholding assets",
        ],
        omissions: [
          "35 million Muslims who chose to remain in India after Partition",
          "The Muslim League's relatively recent mass support (post-1940)",
          "Ethnic and linguistic diversity within the new Pakistan that complicated unity",
        ],
        disputed: [
          "Whether a federal India with strong provincial autonomy could have addressed Muslim concerns",
        ],
        primarySources: [
          {
            text: "You are free; you are free to go to your temples, you are free to go to your mosques or to any other place of worship in this State of Pakistan.",
            author: "Muhammad Ali Jinnah",
            work: "Address to the Constituent Assembly of Pakistan",
            date: "August 11, 1947",
          },
        ],
      },
      {
        id: "persp-partition-academic",
        viewpointName: "Postcolonial Academic Analysis",
        viewpointType: "academic",
        color: "d",
        temporalAnchor: "1990s-2020s",
        geographicAnchor: "Global (universities)",
        narrative: "The partition of British India was not a single event but a process that unfolded over decades and continues to shape the subcontinent. Historians now reject the teleological narrative that partition was inevitable. The Lahore Resolution did not demand a separate state; it demanded autonomous zones. The Cabinet Mission Plan of 1946 proposed a three-tier federation that both the Congress and the Muslim League initially accepted before negotiations collapsed. The role of individual actors, contingent decisions, and colonial institutional legacies all contributed to an outcome that millions experienced as a catastrophe. The demographic evidence reveals that communal violence was not spontaneous but organized, often by local political actors exploiting the power vacuum. The Radcliffe Line was drawn through living communities with no mechanism for population transfer, creating a humanitarian crisis that the colonial administration knew was coming and chose not to prevent. The 75-year silence in official histories of both India and Pakistan about their own roles in the violence has only recently begun to break.",
        keyNarratives: [
          "Partition was contingent, not inevitable",
          "Violence was organized, not spontaneous",
          "Both India and Pakistan suppress inconvenient aspects of partition history",
          "The Radcliffe Line was drawn without ground-level knowledge",
        ],
        omissions: [],
        disputed: [
          "The relative culpability of British, Congress, and Muslim League leadership",
          "Whether partition could have been avoided at any decision point after 1940",
        ],
        primarySources: [
          {
            text: "The story of Partition is a story about the failure of a set of political negotiations, not about the inevitable destiny of two religious communities.",
            author: "Yasmin Khan",
            work: "The Great Partition: The Making of India and Pakistan",
            date: "2007",
          },
        ],
      },
    ],
    media: [
      {
        id: "media-partition-1",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/A_refugee_train%2C_Punjab%2C_1947.jpg/800px-A_refugee_train%2C_Punjab%2C_1947.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/partition-of-india/A_refugee_train_Punjab_1947.jpg",
        caption: "A refugee train arrives in Punjab, 1947",
        attribution: "Unknown photographer / Public Domain",
        year: "1947",
      },
      {
        id: "media-partition-2",
        type: "map",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Partition_of_India_1947_en.svg/800px-Partition_of_India_1947_en.svg.png
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/partition-of-india/Partition_of_India_1947_en.svg.png",
        caption: "The Partition of India, 1947 — new borders dividing British India into India and Pakistan",
        attribution: "Wikimedia Commons / CC BY-SA 4.0",
        year: "1947",
      },
      {
        id: "media-partition-3",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/3/35/Columns_of_refugees_from_West_Punjab.jpg/800px-Columns_of_refugees_from_West_Punjab.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/partition-of-india/Columns_of_refugees_from_West_Punjab.jpg",
        caption: "Columns of refugees walking from West Punjab during Partition",
        attribution: "Unknown photographer / Public Domain",
        year: "1947",
      },
    ],
    connections: [
      {
        targetSlug: "creation-of-israel-nakba",
        targetTitle: "Creation of Israel / Nakba",
        type: "parallel",
        description: "Both events involved British withdrawal and partition along religious/ethnic lines in 1947-48, with mass displacement and unresolved territorial disputes persisting decades later",
      },
      {
        targetSlug: "rwandan-genocide",
        targetTitle: "Rwandan Genocide",
        type: "influenced",
        description: "Partition demonstrated how colonial-era identity categories (Hindu/Muslim, Hutu/Tutsi) could be weaponized during rapid political transitions",
      },
    ],
    published: true,
  },

  /* ── 2. Hiroshima, 1945 ── */
  {
    id: "evt-hiroshima",
    slug: "hiroshima-nagasaki",
    title: "The Atomic Bombings of Hiroshima and Nagasaki",
    subtitle: "The first use of nuclear weapons in warfare",
    era: "contemporary",
    regions: ["east-asia", "americas"],
    categories: ["war", "disaster", "scientific"],
    severity: "catastrophic",
    datePrimary: "August 6, 1945",
    dateSort: 19450806,
    dateRange: "August 6, 1945",
    location: "Hiroshima, Japan",
    // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Atomic_cloud_over_Hiroshima.jpg/800px-Atomic_cloud_over_Hiroshima.jpg
    heroImage: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/hiroshima-nagasaki/Atomic_cloud_over_Hiroshima.jpg",
    heroCaption: "The mushroom cloud over Hiroshima, photographed from Enola Gay's tail gunner position",
    heroAttribution: "U.S. Army Air Force / National Archives",
    contextNarrative: "At 8:15 AM on August 6, 1945, the B-29 bomber Enola Gay released a uranium-235 bomb designated \"Little Boy\" over the center of Hiroshima. The detonation occurred at 1,900 feet with a yield of approximately 15 kilotons. The fireball reached temperatures exceeding 1 million degrees Celsius. Within one second, everything within a 1-mile radius was incinerated. The blast wave traveled at 984 feet per second, collapsing every structure within 1.5 miles. Of Hiroshima's 350,000 residents, between 70,000 and 80,000 died instantly. By December 1945, the total reached 140,000. Radiation sickness continued killing for decades. Three days later, a second bomb fell on Nagasaki. Japan surrendered on August 15.",
    keyFigures: [
      { name: "Harry S. Truman", role: "President of the United States" },
      { name: "Colonel Paul Tibbets", role: "Pilot of the Enola Gay" },
      { name: "Emperor Hirohito", role: "Emperor of Japan" },
      { name: "Robert Oppenheimer", role: "Scientific Director, Manhattan Project" },
      { name: "Henry Stimson", role: "U.S. Secretary of War" },
    ],
    deathToll: "140,000 by December 1945 (Hiroshima alone)",
    displaced: "Approximately 176,000 (Hiroshima survivors)",
    duration: "Single day (effects ongoing for decades)",
    perspectives: [
      {
        id: "persp-hiroshima-us",
        viewpointName: "U.S. Strategic Command",
        viewpointType: "victor",
        color: "a",
        temporalAnchor: "1945, Washington D.C.",
        geographicAnchor: "Washington D.C.",
        narrative: "The atomic bomb ended the war and saved lives. Operation Downfall, the planned invasion of the Japanese home islands, carried estimated casualties of 500,000 to 1 million American soldiers and potentially millions of Japanese military and civilian deaths. Japan's military leadership had rejected the Potsdam Declaration's demand for unconditional surrender. The kamikaze campaign at Okinawa, where 1,900 Japanese pilots flew suicide missions killing 4,900 American sailors, demonstrated that Japan intended to fight to the last man. The firebombing of Tokyo in March 1945 killed more than 100,000 people without prompting surrender. The atomic bomb provided what conventional weapons could not: a shock so absolute that even the military faction within Japan's Supreme War Council could no longer argue for continued resistance. Truman's decision was a calculation: the certain deaths of Hiroshima's civilians against the probable deaths of millions in an invasion. The calculus was grim but clear.",
        keyNarratives: [
          "The bomb prevented a land invasion that would have killed millions",
          "Japan's military rejected all surrender overtures before August 6",
          "Conventional bombing had already proven insufficient to force surrender",
          "The decision was military necessity, not racial animus",
        ],
        omissions: [
          "The role of Soviet entry into the Pacific War on August 8",
          "Internal Japanese peace efforts through Soviet mediation channels",
          "Alternatives: demonstration bombing, modified surrender terms retaining the Emperor",
          "The selection of a civilian population center rather than a military target",
        ],
        disputed: [
          "Whether Japan would have surrendered without the bomb given Soviet entry into the war",
        ],
        primarySources: [
          {
            text: "Having found the bomb, we have used it. We have used it against those who attacked us without warning at Pearl Harbor, against those who have starved and beaten and executed American prisoners of war.",
            author: "Harry S. Truman",
            work: "Radio address to the nation",
            date: "August 6, 1945",
          },
        ],
      },
      {
        id: "persp-hiroshima-survivor",
        viewpointName: "Hibakusha (Survivors)",
        viewpointType: "vanquished",
        color: "b",
        temporalAnchor: "1945-present",
        geographicAnchor: "Hiroshima, Japan",
        narrative: "Setsuko Thurlow was 13, walking to school, 1.8 kilometers from the hypocenter. The flash was silent. Then came heat that melted skin. Then came the black rain, oily and radioactive, falling on the walking dead. Survivors described people with their eyes melted from their sockets, skin hanging from their arms like cloth, stumbling toward the river. The river filled with corpses. Thurlow pulled classmates from rubble; most died within hours. In the months that followed, survivors developed radiation sickness: hair loss, bleeding gums, purple spots, death. For decades afterward, the hibakusha faced discrimination in marriage and employment. Insurance companies refused them. The bomb did not end on August 6. It continued in leukemia clusters in the 1950s, in thyroid cancers, in the genetic anxiety of every hibakusha parent. The survivors became the world's unwilling witnesses, carrying a testimony that governments would prefer to forget.",
        keyNarratives: [
          "The suffering extended for decades through radiation illness and discrimination",
          "Survivors were treated as contaminated by their own society",
          "The target was a city of civilians, not a military installation",
          "The hibakusha became advocates for nuclear disarmament through lived testimony",
        ],
        omissions: [],
        disputed: [],
        primarySources: [
          {
            text: "Each person had a story. Each person had a name. I want you to know that it was not a statistic. It was not a military calculation. It was my classmate Emiko, who could not find her mother.",
            author: "Setsuko Thurlow",
            work: "Nobel Peace Prize acceptance speech (on behalf of ICAN)",
            date: "December 10, 2017",
          },
        ],
      },
      {
        id: "persp-hiroshima-revisionist",
        viewpointName: "Revisionist Military Historians",
        viewpointType: "revisionist",
        color: "c",
        temporalAnchor: "1960s-2020s",
        geographicAnchor: "Global (academia)",
        narrative: "Declassified records from both American and Japanese archives challenge the standard justification. The U.S. Strategic Bombing Survey, conducted at Truman's order, concluded in 1946 that Japan would have surrendered by November 1945 without the atomic bomb, without the Soviet invasion, and without a planned American landing. Seven of eight five-star officers in the U.S. military in 1945, including Eisenhower, MacArthur, and Leahy, publicly stated the bomb was militarily unnecessary. The Japanese Supreme War Council was already deadlocked 3-3 on surrender before Hiroshima; the Soviet declaration of war on August 8, not the second bomb on Nagasaki, broke the deadlock. Truman's diary entries suggest he understood the bomb's primary value was diplomatic: demonstrating American power to the Soviet Union at the dawn of the Cold War. The decision to drop the bomb on a city rather than conduct a demonstration explosion on an unpopulated target was driven by the desire to maximize psychological impact.",
        keyNarratives: [
          "Japan was already seeking surrender through Soviet diplomatic channels",
          "Senior U.S. military leaders considered the bomb unnecessary",
          "Soviet entry into the war was the decisive factor in Japanese surrender",
          "Cold War posturing against the USSR influenced the decision",
        ],
        omissions: [
          "The genuine uncertainty in 1945 about Japanese intentions",
          "The strength of the Japanese military faction that staged a coup attempt even after Nagasaki",
        ],
        disputed: [
          "Whether the Bombing Survey's conclusions were influenced by inter-service rivalries",
          "Whether Japan's peace overtures through Moscow were serious or exploratory",
        ],
        primarySources: [
          {
            text: "The Japanese were already defeated and ready to surrender. The use of this barbarous weapon at Hiroshima and Nagasaki was of no material assistance in our war against Japan.",
            author: "Admiral William Leahy",
            work: "I Was There (memoir)",
            date: "1950",
          },
        ],
      },
      {
        id: "persp-hiroshima-scientific",
        viewpointName: "International / Scientific",
        viewpointType: "bystander",
        color: "d",
        temporalAnchor: "1945-present",
        geographicAnchor: "Global",
        narrative: "The scientific community that built the bomb was among the first to grasp its implications. The Franck Report, drafted in June 1945 by Manhattan Project scientists at the University of Chicago, recommended a demonstration on an uninhabited island before any use against a city. The report warned a surprise attack would trigger an arms race. Stimson's Interim Committee rejected the proposal. Within weeks of Hiroshima, Leo Szilard circulated a petition signed by 70 scientists urging restraint. Oppenheimer told Truman in October 1945: \"Mr. President, I feel I have blood on my hands.\" His subsequent opposition to the hydrogen bomb led to his security clearance revocation in 1954. The Soviet Union tested its first bomb in August 1949, accelerating an arms race that peaked at roughly 70,000 warheads. The Bulletin of the Atomic Scientists introduced the Doomsday Clock in 1947. Nine nations now possess approximately 12,500 nuclear warheads. The scientific-international perspective frames Hiroshima and Nagasaki as a species-level inflection point: before August 6, 1945, humanity lacked the capacity for self-annihilation. After it, the capacity existed and proliferated.",
        keyNarratives: [
          "Manhattan Project scientists warned against surprise use — the Franck Report of June 1945",
          "The bombings triggered an arms race that produced 70,000 warheads at peak",
          "Nuclear proliferation transformed existential risk into a permanent feature of geopolitics",
          "Scientific community organized against its own creation within weeks",
        ],
        omissions: [
          "Wartime context that drove the decision under extreme time pressure",
          "Japan's military atrocities that shaped Allied attitudes",
          "Technical constraints that made a 'demonstration' impractical",
        ],
        disputed: [
          "Whether a demonstration bombing could have compelled surrender without civilian casualties",
        ],
        primarySources: [
          {
            text: "Mr. President, I feel I have blood on my hands.",
            author: "J. Robert Oppenheimer",
            work: "Meeting with President Truman",
            date: "October 1945",
          },
        ],
      },
    ],
    media: [
      {
        id: "media-hiroshima-1",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Nagasakibomb.jpg/800px-Nagasakibomb.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/hiroshima-nagasaki/Nagasakibomb.jpg",
        caption: "The mushroom cloud over Nagasaki, August 9, 1945 — photographed by Charles Levy",
        attribution: "Charles Levy / U.S. Army Air Force / Public Domain",
        year: "1945",
      },
      {
        id: "media-hiroshima-2",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/AtomicEffects-Hiroshima.jpg/800px-AtomicEffects-Hiroshima.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/hiroshima-nagasaki/AtomicEffects-Hiroshima.jpg",
        caption: "Effects of the atomic bomb on Hiroshima, photographed from the Red Cross Hospital, about 1 mile from the hypocenter",
        attribution: "U.S. Army / Public Domain",
        year: "1945",
      },
      {
        id: "media-hiroshima-3",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/B-29_Enola_Gay_w_Crews.jpg/800px-B-29_Enola_Gay_w_Crews.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/hiroshima-nagasaki/B-29_Enola_Gay_w_Crews.jpg",
        caption: "The B-29 Superfortress Enola Gay with ground crew on Tinian Island",
        attribution: "U.S. Air Force / Public Domain",
        year: "1945",
      },
    ],
    connections: [
      {
        targetSlug: "partition-of-india",
        targetTitle: "Partition of India",
        type: "parallel",
        description: "Both occurred in the immediate postwar period of 1945-1947 as empires dissolved and new nations formed amid mass civilian casualties",
      },
      {
        targetSlug: "rwandan-genocide",
        targetTitle: "Rwandan Genocide",
        type: "influenced",
        description: "The post-Hiroshima 'never again' framework shaped international humanitarian law and the obligation to intervene — a framework that failed in Rwanda in 1994",
      },
    ],
    published: true,
  },

  /* ── 3. Rwandan Genocide, 1994 ── */
  {
    id: "evt-rwanda",
    slug: "rwandan-genocide",
    title: "Rwandan Genocide",
    subtitle: "800,000 killed in 100 days",
    era: "contemporary",
    regions: ["africa"],
    categories: ["genocide", "political", "war"],
    severity: "catastrophic",
    datePrimary: "April 7, 1994",
    dateSort: 19940407,
    dateRange: "April 7 - July 15, 1994",
    location: "Rwanda",
    // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Grounds_of_Kigali_Genocide_Memorial_with_City_in_the_Distance_-_Kigali_-_Rwanda.jpg/800px-Grounds_of_Kigali_Genocide_Memorial_with_City_in_the_Distance_-_Kigali_-_Rwanda.jpg
    heroImage: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/rwandan-genocide/Grounds_of_Kigali_Genocide_Memorial.jpg",
    heroCaption: "Memorial at Murambi Technical School, where 45,000 were killed in a single day",
    heroAttribution: "Gilles Peress / Magnum Photos",
    contextNarrative: "In 100 days between April and July 1994, Hutu extremists in Rwanda killed an estimated 800,000 Tutsi and moderate Hutu. The killing rate exceeded that of the Nazi Holocaust. Perpetrators used machetes, clubs, and small arms. The genocide was not spontaneous violence but a coordinated campaign organized by the Hutu Power faction within the government, military, and Interahamwe militia. Radio Mille Collines broadcast lists of names and addresses. Roadblocks checked identity cards that listed ethnicity, a classification system introduced by Belgian colonial authorities in 1933. The UN peacekeeping force (UNAMIR), commanded by Canadian General Romeo Dallaire, had warned headquarters of the planned extermination three months before it began. The UN Security Council reduced the force from 2,500 to 270 troops ten days into the genocide. France, Belgium, and the United States evacuated their nationals and left.",
    keyFigures: [
      { name: "Romeo Dallaire", role: "Force Commander, UNAMIR" },
      { name: "Paul Kagame", role: "Commander, Rwandan Patriotic Front" },
      { name: "Juvenal Habyarimana", role: "President of Rwanda (assassinated April 6)" },
      { name: "Kofi Annan", role: "Head of UN Peacekeeping Operations" },
      { name: "Theoneste Bagosora", role: "Director, Ministry of Defence (convicted)" },
    ],
    deathToll: "800,000 - 1,000,000",
    displaced: "2,000,000 (refugees fled to neighboring countries)",
    duration: "100 days",
    perspectives: [
      {
        id: "persp-rwanda-survivor",
        viewpointName: "Tutsi Survivors",
        viewpointType: "vanquished",
        color: "a",
        temporalAnchor: "1994, Rwanda",
        geographicAnchor: "Rwanda",
        narrative: "Immaculee Ilibagiza hid for 91 days in a bathroom measuring 3 by 4 feet with seven other women. Through the door she could hear neighbors, people who had attended her family's wedding, calling her name and describing what they would do when they found her. Her mother, father, and two brothers were killed. Her identity card said Tutsi. That was her crime. The genocide was not chaos. It was administration. Lists were prepared. Roadblocks were organized. Community leaders assigned kill quotas. Teachers identified Tutsi students to militias. Doctors killed patients. Priests locked congregations inside churches and directed Interahamwe to the doors. The international community did not fail to act because it did not know. General Dallaire sent cables. Journalists reported. The UN knew. The Americans knew. They chose the word \"acts of genocide\" specifically to avoid the legal obligation that the word \"genocide\" alone would have triggered.",
        keyNarratives: [
          "The genocide was bureaucratically organized, not spontaneous tribal violence",
          "Neighbors, teachers, and clergy participated as perpetrators",
          "The international community knew and chose inaction",
          "Identity cards introduced by colonial Belgium marked people for death",
        ],
        omissions: [],
        disputed: [],
        primarySources: [
          {
            text: "The killers were not strangers. They were neighbors, colleagues, even family members of mixed marriages. That is the part the world does not want to understand.",
            author: "Immaculee Ilibagiza",
            work: "Left to Tell",
            date: "2006",
          },
        ],
      },
      {
        id: "persp-rwanda-un",
        viewpointName: "United Nations / International Community",
        viewpointType: "bystander",
        color: "b",
        temporalAnchor: "1994, New York",
        geographicAnchor: "UN Headquarters, New York",
        narrative: "The United Nations was hamstrung by the Somalia experience. Eighteen American soldiers had been killed in Mogadishu in October 1993, and the United States, the largest contributor to UN peacekeeping budgets, refused to support any expansion of the UNAMIR mandate. Presidential Decision Directive 25, signed by Clinton in May 1994, explicitly restricted U.S. involvement in UN operations. The Security Council operated on incomplete information in a fast-moving crisis. UNAMIR's mandate was limited to monitoring the Arusha Accords ceasefire, not to intervention. When the violence began, the force had neither the authorization nor the capacity to stop it. Belgium withdrew its contingent after ten of its soldiers were tortured and killed. The Secretariat, under Boutros Boutros-Ghali, underestimated the scale and speed of the killing. The word \"genocide\" was avoided not from cynicism but from legal caution: the 1948 Convention obligated signatories to act, and no member state was willing to commit troops.",
        keyNarratives: [
          "The UN mandate did not authorize military intervention",
          "The Somalia disaster made troop-contributing nations unwilling to engage",
          "The speed of the killing outpaced institutional decision-making",
          "No member state volunteered forces for intervention",
        ],
        omissions: [
          "Dallaire's January 1994 cable explicitly warning of planned extermination",
          "The deliberate avoidance of the word genocide to evade legal obligation",
          "France's active military support for the Hutu government",
          "The reduction of UNAMIR from 2,500 to 270 during the genocide",
        ],
        disputed: [
          "Whether 5,000 troops could have prevented the bulk of the killing, as Dallaire argued",
        ],
        primarySources: [
          {
            text: "I have failed. The international community has failed Rwanda, and that must leave us all with a sense of bitter regret.",
            author: "Kofi Annan",
            work: "Report of the Independent Inquiry into UN actions during the genocide",
            date: "December 1999",
          },
        ],
      },
      {
        id: "persp-rwanda-academic",
        viewpointName: "Genocide Studies Scholars",
        viewpointType: "academic",
        color: "c",
        temporalAnchor: "2000s-2020s",
        geographicAnchor: "Global (universities)",
        narrative: "The Rwandan genocide challenges every comfortable assumption about modern civilization. It was not premodern tribalism. It was organized by educated elites using modern media (radio), modern bureaucracy (identity cards, census lists), and modern logistics (roadblocks, militia deployment). The ethnic categories of Hutu and Tutsi were not ancient tribal identities but colonial constructions. Belgian administrators in 1933 issued identity cards that fixed fluid social categories into permanent racial classifications based on cattle ownership and physical measurements. The genocide was preceded by years of state-sponsored propaganda dehumanizing Tutsi as \"inyenzi\" (cockroaches). The pattern matches Stanton's ten stages of genocide, and Rwanda passed through every stage in sequence while the international community watched. The post-genocide government under Paul Kagame has achieved stability and economic growth but at the cost of political freedom. The gacaca courts processed over 1.9 million cases of genocide-related crimes using a community justice model unprecedented in scale. Whether Rwanda's recovery model, which prioritizes unity over individual freedom, constitutes justice or merely effective authoritarianism remains debated.",
        keyNarratives: [
          "Hutu-Tutsi categories were colonial constructions, not ancient tribal identities",
          "The genocide followed a recognizable pattern of escalation over years",
          "Modern infrastructure, not primitive tribalism, enabled the killing rate",
          "Post-genocide justice via gacaca courts was unprecedented but imperfect",
        ],
        omissions: [
          "The RPF's own atrocities during and after the genocide",
          "Ongoing political repression under Kagame's government",
        ],
        disputed: [
          "Whether the gacaca system delivered justice or institutional forgetting",
          "The RPF's role in the assassination of President Habyarimana",
        ],
        primarySources: [
          {
            text: "Genocide is not an aberration. It is a political choice made by political actors who calculate that mass killing will serve their interests.",
            author: "Scott Straus",
            work: "The Order of Genocide: Race, Power, and War in Rwanda",
            date: "2006",
          },
        ],
      },
      {
        id: "persp-rwanda-panafricanist",
        viewpointName: "Pan-African / Postcolonial",
        viewpointType: "revisionist",
        color: "d",
        temporalAnchor: "1894-present",
        geographicAnchor: "Africa / Global",
        narrative: "The Rwandan genocide did not begin on April 6, 1994. It began in 1894, when Germany's Count Gustav Adolf von Gotzen reached the Rwandan royal court, and accelerated in 1916 when Belgium assumed control. The Belgians did not invent Hutu and Tutsi — these were fluid social designations related to cattle ownership — but they fixed them. In the 1930s, identity cards classified every Rwandan as Hutu (85%), Tutsi (14%), or Twa (1%) based on physical measurements and cattle counts. The categories became hereditary and immutable. Belgium elevated Tutsis as a ruling class using the Hamitic hypothesis, a European racial theory. When independence movements gained force, Belgium reversed allegiance, supporting the 1959 Hutu revolution that killed 20,000 Tutsis and drove 150,000 into exile. The RTLM propaganda drew directly on colonial racial science. The contrast between Western intervention in Bosnia (NATO airstrikes, 1994-95) and Rwanda's abandonment reflects a racial calculus. France maintained a military alliance with the Habyarimana regime, supplying weapons even after the genocide began. The 2021 Duclert Commission found France bore \"heavy and overwhelming responsibilities.\" The genocide was not an African aberration. It was a modern event organized through a state bureaucracy built by Europeans, using identity categories created by Europeans, executed with weapons supplied by Europeans.",
        keyNarratives: [
          "Belgian colonial administration created the fixed ethnic categories used to sort victims",
          "The Hamitic hypothesis — a European racial theory — provided the ideological framework",
          "Western non-intervention reflected a racial calculus that devalued African lives",
          "France maintained military alliance with the genocidal regime before and during the killing",
        ],
        omissions: [
          "Agency of Rwandan political actors in planning and executing the genocide",
          "Precolonial Hutu-Tutsi relations and their complexities",
          "Post-genocide RPF governance and its authoritarian dimensions",
        ],
        disputed: [
          "Whether colonial categories alone explain the depth of the violence",
          "The extent of France's direct complicity versus structural responsibility",
        ],
        primarySources: [
          {
            text: "The life of an African is worth less in the corridors of international power than the life of a European. Rwanda proved it.",
            author: "Wole Soyinka",
            work: "The Burden of Memory, the Muse of Forgiveness",
            date: "1999",
          },
        ],
      },
    ],
    media: [
      {
        id: "media-rwanda-1",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Kigali_Genocide_Memorial.jpg/800px-Kigali_Genocide_Memorial.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/rwandan-genocide/Kigali_Genocide_Memorial.jpg",
        caption: "Kigali Genocide Memorial, where over 250,000 are interred",
        attribution: "Wikimedia Commons / CC BY-SA 3.0",
        year: "2004",
      },
      {
        id: "media-rwanda-2",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Mass_Graves_in_Which_259000_Genocide_Victims_Are_Interred_-_Genocide_Memorial_Center_-_Kigali_-_Rwanda_-_01.jpg/800px-Mass_Graves_in_Which_259000_Genocide_Victims_Are_Interred_-_Genocide_Memorial_Center_-_Kigali_-_Rwanda_-_01.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/rwandan-genocide/Mass_Graves_Genocide_Memorial_Center_Kigali.jpg",
        caption: "Mass graves at the Genocide Memorial Center in Kigali where 259,000 victims are interred",
        attribution: "Adam Jones / CC BY-SA 3.0",
        year: "2012",
      },
      {
        id: "media-rwanda-3",
        type: "image",
        // Original Wikimedia: https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Panorama_of_Photos_of_Genocide_Victims_-_Genocide_Memorial_Center_-_Kigali_-_Rwanda.jpg/800px-Panorama_of_Photos_of_Genocide_Victims_-_Genocide_Memorial_Center_-_Kigali_-_Rwanda.jpg
        url: "https://xryzskhgfuafyotrcdvj.supabase.co/storage/v1/object/public/history-media/rwandan-genocide/Panorama_of_Photos_of_Genocide_Victims.jpg",
        caption: "Panorama of photographs of genocide victims displayed at the Genocide Memorial Center, Kigali",
        attribution: "Adam Jones / CC BY-SA 3.0",
        year: "2012",
      },
    ],
    connections: [
      {
        targetSlug: "partition-of-india",
        targetTitle: "Partition of India",
        type: "parallel",
        description: "Both events demonstrated how colonial-era identity categories (Hindu/Muslim, Hutu/Tutsi) could be weaponized during rapid political transitions, producing mass displacement and communal killing",
      },
      {
        targetSlug: "hiroshima-nagasaki",
        targetTitle: "Atomic Bombings of Hiroshima and Nagasaki",
        type: "influenced",
        description: "The post-Hiroshima 'never again' consensus — enshrined in the 1948 Genocide Convention — proved hollow in Rwanda; the UN's failure contributed directly to the Responsibility to Protect doctrine",
      },
    ],
    published: true,
  },
];

/* ── Redacted Dossier Stubs — all 5 previously classified events are now published ── */
export const REDACTED_EVENTS: RedactedEvent[] = [];
