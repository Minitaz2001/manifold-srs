"""
M3 Workstream D Builder — Natural World Visual Pack (~150 items, NYC & Northeast focus).
Queries Wikimedia Commons API directly, enforces open licenses (PD / CC0 / CC-BY / CC-BY-SA),
downloads lightweight 360px offline thumbnails into public/media/natural-world/, and stores
exact artist, license, and Commons file URL per card. Skips already-downloaded thumbnails cleanly.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.2 (offline educational build; https://github.com/manifold-srs)"}
ALLOWED_LICENSE_PATTERNS = ("cc", "public domain", "pd", "cc0")

# ~145 iconic NYC / Northeast trees, birds, clouds/weather, rocks/minerals, plants/fungi, insects/mammals, constellations
SPECIMENS = [
    # ==================== TREES (40) ====================
    ("red-maple", "Red Maple (Acer rubrum)", "tree", "Acer rubrum leaf", "Opposite toothed 3–5 lobed leaf; red petioles; dominant Northeast wetland/upland deciduous tree."),
    ("sugar-maple", "Sugar Maple (Acer saccharum)", "tree", "Acer saccharum leaf", "Opposite 5-lobed leaf with smooth U-shaped sinuses (no fine teeth); source of maple syrup."),
    ("norway-maple", "Norway Maple (Acer platanoides)", "tree", "Acer platanoides leaf", "Broad 5–7 pointed lobes; milky white sap when leaf stalk breaks; common invasive NYC street tree."),
    ("silver-maple", "Silver Maple (Acer saccharinum)", "tree", "Acer saccharinum leaf", "Deeply cut 5-lobed opposite leaves with silvery-white undersides; fast-growing floodplain tree."),
    ("boxelder", "Boxelder (Acer negundo)", "tree", "Acer negundo leaf", "Only native Northeast maple with compound (3–5 leaflet) opposite leaves; green twigs."),
    ("eastern-white-pine", "Eastern White Pine (Pinus strobus)", "tree", "Pinus strobus needles", "Only native Northeast pine with needles in bundles of 5 ('W-H-I-T-E'); feathery blue-green plumes."),
    ("pitch-pine", "Pitch Pine (Pinus rigida)", "tree", "Pinus rigida needles", "Twisted needles in bundles of 3 sprouting straight from dark scaly bark; Pine Barrens fire-adapted tree."),
    ("eastern-hemlock", "Eastern Hemlock (Tsuga canadensis)", "tree", "Tsuga canadensis needles", "Flat lacy sprays of short blunt needles with two white stomatal stripes underneath; shade-tolerant ravine conifer."),
    ("eastern-redcedar", "Eastern Redcedar (Juniperus virginiana)", "tree", "Juniperus virginiana berries", "Scale-like foliage, fibrous peeling red-brown bark, and dusty blue berry-like cones; colonizes old fields."),
    ("balsam-fir", "Balsam Fir (Abies balsamea)", "tree", "Abies balsamea", "Flat fragrant needles on smooth resin-blistered bark; upright cones; classic Northeast boreal conifer."),
    ("northern-red-oak", "Northern Red Oak (Quercus rubra)", "tree", "Quercus rubra leaf", "Pointed bristle-tipped lobes (red oak group); flat saucer-like acorn cap; ski-track bark ridges."),
    ("white-oak", "White Oak (Quercus alba)", "tree", "Quercus alba leaf", "Rounded bristle-free lobes; light ash-gray scaly bark; deep warty acorn cup; prized timber."),
    ("pin-oak", "Pin Oak (Quercus palustris)", "tree", "Quercus palustris leaf", "Deeply cut bristle-tipped lobes; lower branches droop down, middle horizontal, top upward; common NYC street tree."),
    ("chestnut-oak", "Chestnut Oak (Quercus montana)", "tree", "Quercus montana bark", "Deeply furrowed dark chunky bark; wavy scalloped margin leaves; dry Northeast ridgetops."),
    ("american-sycamore", "American Sycamore (Platanus occidentalis)", "tree", "Platanus occidentalis bark", "Camouflage exfoliating bark (white, olive, brown); broad maple-like leaves; single fuzzy seed balls."),
    ("london-plane", "London Plane (Platanus x acerifolia)", "tree", "Platanus x acerifolia bark", "Hybrid sycamore dominant on NYC avenues; olive-cream flaking bark and seed balls hanging in PAIRS."),
    ("paper-birch", "Paper Birch (Betula papyrifera)", "tree", "Betula papyrifera bark", "Chalky white peeling bark with horizontal dark lenticels; cool northern woods."),
    ("yellow-birch", "Yellow Birch (Betula alleghaniensis)", "tree", "Betula alleghaniensis bark", "Metallic bronze-gold curling papery bark; twigs smell strongly of wintergreen when scratched."),
    ("black-birch", "Sweet / Black Birch (Betula lenta)", "tree", "Betula lenta bark", "Dark cherry-like smooth bark with horizontal lenticels; intense wintergreen-scented twigs."),
    ("river-birch", "River Birch (Betula nigra)", "tree", "Betula nigra bark", "Shaggy cinnamon-salmon peeling bark; heat-tolerant ornamental and streamside birch."),
    ("ginkgo-biloba", "Ginkgo (Ginkgo biloba)", "tree", "Ginkgo biloba leaf", "Unmistakable fan-shaped leaf with dichotomous veins; living fossil ubiquitous as an NYC street tree."),
    ("american-beech", "American Beech (Fagus grandifolia)", "tree", "Fagus grandifolia bark", "Smooth elephant-skin silver-gray bark; serrated parallel-veined leaves clinging tan through winter."),
    ("tulip-poplar", "Tulip Tree (Liriodendron tulipifera)", "tree", "Liriodendron tulipifera leaf", "Four-lobed cat-face leaf with flat notched tip; tallest straight-trunked Eastern hardwood."),
    ("sweetgum", "American Sweetgum (Liquidambar styraciflua)", "tree", "Liquidambar styraciflua leaf", "Symmetric 5-pointed star leaf; corky twig wings; spiky woody 'gumball' fruits."),
    ("black-cherry", "Black Cherry (Prunus serotina)", "tree", "Prunus serotina bark", "Dark flaky 'burnt potato chip' bark; narrow finely toothed leaves with rusty hairs along midrib."),
    ("american-elm", "American Elm (Ulmus americana)", "tree", "Ulmus americana", "Graceful vase-shaped crown; lopsided doubly serrated sandpaper leaves; decimated by Dutch elm disease."),
    ("honeylocust", "Honeylocust (Gleditsia triacanthos)", "tree", "Gleditsia triacanthos leaf", "Airy bipinnately compound leaflets giving dappled shade; thornless cultivar dominates NYC sidewalks."),
    ("black-locust", "Black Locust (Robinia pseudoacacia)", "tree", "Robinia pseudoacacia bark", "Deeply braided rope-like bark; pinnately compound oval leaflets; ultra-rot-resistant fence-post wood."),
    ("sassafras", "Sassafras (Sassafras albidum)", "tree", "Sassafras albidum leaf", "Three distinct leaf shapes on one branch (oval, mitten, three-lobed); green citrus-scented twigs."),
    ("shagbark-hickory", "Shagbark Hickory (Carya ovata)", "tree", "Carya ovata bark", "Long vertical curling plates of gray bark; 5-leaflet compound leaf with huge terminal leaflets."),
    ("black-walnut", "Black Walnut (Juglans nigra)", "tree", "Juglans nigra fruit", "Long pinnate leaves (15–23 leaflets); aromatic green husk nuts; chocolate-brown prized heartwood."),
    ("white-ash", "White Ash (Fraxinus americana)", "tree", "Fraxinus americana bark", "Diamond-patterned interlacing bark ridges; opposite compound leaves (7 leaflets); baseball bat wood."),
    ("weeping-willow", "Weeping Willow (Salix babylonica)", "tree", "Salix babylonica", "Long pendulous golden-green whip branches with narrow lance-shaped leaves; always near water."),
    ("eastern-cottonwood", "Eastern Cottonwood (Populus deltoides)", "tree", "Populus deltoides leaf", "Triangular heart-shaped leaves on flattened petioles that tremble in light wind; deep furrowed bark."),
    ("quaking-aspen", "Quaking Aspen (Populus tremuloides)", "tree", "Populus tremuloides bark", "Chalky pale greenish-white bark with black eye knots; clonal root groves; round trembling leaves."),
    ("flowering-dogwood", "Flowering Dogwood (Cornus florida)", "tree", "Cornus florida flower", "Opposite leaves with arcuate veins curving toward tip; 4 white notched bracts in spring; alligator-checkered bark."),
    ("eastern-redbud", "Eastern Redbud (Cercis canadensis)", "tree", "Cercis canadensis flower", "Magenta pea-like blossoms erupting directly from bare spring branches (cauliflory); heart-shaped leaves."),
    ("american-holly", "American Holly (Ilex opaca)", "tree", "Ilex opaca", "Broadleaf evergreen with stiff spiny matte green leaves and bright red winter berries on females."),
    ("tree-of-heaven", "Tree of Heaven (Ailanthus altissima)", "tree", "Ailanthus altissima leaf", "Huge compound leaves with glandular basal notch and burnt-peanut odor; invasive Brooklyn backyard weed-tree."),
    ("bald-cypress", "Bald Cypress (Taxodium distichum)", "tree", "Taxodium distichum", "Deciduous conifer with soft feathery needles turning rust-orange in autumn; fluted buttress base and 'knees'."),

    # ==================== BIRDS (40) ====================
    ("red-tailed-hawk", "Red-tailed Hawk (Buteo jamaicensis)", "bird", "Buteo jamaicensis perched", "Broad-winged soaring raptor; dark belly band and rust-red upper tail; common over NYC parks and highways."),
    ("peregrine-falcon", "Peregrine Falcon (Falco peregrinus)", "bird", "Falco peregrinus perched", "Dark malar 'helmet' stripe, slate back, barred breast; fastest animal in a stoop (>300 km/h); nests on bridges."),
    ("american-kestrel", "American Kestrel (Falco sparverius)", "bird", "Falco sparverius", "North America's smallest falcon; rusty back/tail, blue-gray wings on males, double black facial bars; hovers over fields."),
    ("coopers-hawk", "Cooper's Hawk (Accipiter cooperii)", "bird", "Accipiter cooperii", "Long barred tail and short rounded wings for weaving through trees hunting songbirds; dark cap, fiery red eye."),
    ("bald-eagle", "Bald Eagle (Haliaeetus leucocephalus)", "bird", "Haliaeetus leucocephalus", "White head and tail, massive yellow bill, 2 m flat-winged soar; winters along the Hudson River."),
    ("osprey", "Osprey (Pandion haliaetus)", "bird", "Pandion haliaetus", "Fish-hunting raptor with crisp white underside, dark eye-stripe, and M-shaped crooked wings; huge stick nests on channel markers."),
    ("great-horned-owl", "Great Horned Owl (Bubo virginianus)", "bird", "Bubo virginianus", "Large powerful nocturnal owl with prominent ear tufts ('horns'), white throat bib, and deep 5-syllable hoot."),
    ("barred-owl", "Barred Owl (Strix varia)", "bird", "Strix varia", "Round earless head, dark soulful eyes, vertical belly streaks; calls 'who cooks for you?'."),
    ("great-blue-heron", "Great Blue Heron (Ardea herodias)", "bird", "Ardea herodias", "Tall slate-blue wading bird (~1.2 m) with S-curved neck in flight and yellow dagger bill."),
    ("great-egret", "Great Egret (Ardea alba)", "bird", "Ardea alba", "Snow-white tall heron with yellow dagger bill and glossy black legs/feet."),
    ("black-crowned-night-heron", "Black-crowned Night-Heron (Nycticorax nycticorax)", "bird", "Nycticorax nycticorax", "Stocky hunched heron with black crown/back, pale gray wings, and ruby-red eyes; active at dusk in NYC parks."),
    ("double-crested-cormorant", "Double-crested Cormorant (Nannopterum auritum)", "bird", "Phalacrocorax auritus", "Dark prehistoric-looking diving bird with hooked orange-throated bill; perches spreading wings to dry."),
    ("canada-goose", "Canada Goose (Branta canadensis)", "bird", "Branta canadensis", "Black head and neck with white chinstrap; V-formation migrant and permanent urban park resident."),
    ("mallard", "Mallard (Anas platyrhynchos)", "bird", "Anas platyrhynchos male", "Iridescent green head, yellow bill, white neck ring on drake; mottled brown female with violet wing speculum."),
    ("wood-duck", "Wood Duck (Aix sponsa)", "bird", "Aix sponsa male", "Ornate crested male with emerald-violet head and crisp white facial stripes; nests in tree cavities."),
    ("herring-gull", "Herring Gull (Larus argentatus)", "bird", "Larus argentatus", "Large classic NYC coastal gull: pale gray mantle, black wingtips, pink legs, yellow bill with red spot."),
    ("belted-kingfisher", "Belted Kingfisher (Megaceryle alcyon)", "bird", "Megaceryle alcyon", "Shaggy blue-gray crest, heavy dagger bill, rattling call; hovers then plunges headfirst for minnows."),
    ("rock-pigeon", "Rock Pigeon (Columba livia)", "bird", "Columba livia", "Urban cliff-dweller descended from wild cliff doves; double black wing bars and iridescent neck sheen."),
    ("mourning-dove", "Mourning Dove (Zenaida macroura)", "bird", "Zenaida macroura", "Sleek fawn-brown dove with pointed tail, whistling wingbeats on takeoff, and soft 'coo-OO-oo' song."),
    ("downy-woodpecker", "Downy Woodpecker (Dryobates pubescens)", "bird", "Dryobates pubescens", "Smallest North American woodpecker; crisp white back stripe, tiny stubby bill, red nape patch on male."),
    ("red-bellied-woodpecker", "Red-bellied Woodpecker (Melanerpes carolinus)", "bird", "Melanerpes carolinus", "Zebra-striped black-and-white back with bright crimson cap/nape (barely visible reddish belly blush)."),
    ("northern-flicker", "Northern Flicker (Colaptes auratus)", "bird", "Colaptes auratus", "Brown spotted ground-foraging ant-eating woodpecker; black chest crescent, white rump, golden-yellow underwings."),
    ("pileated-woodpecker", "Pileated Woodpecker (Dryocopus pileatus)", "bird", "Dryocopus pileatus", "Crow-sized forest woodpecker with flaming red triangular crest; chisels huge rectangular holes in dead timber."),
    ("blue-jay", "Blue Jay (Cyanocitta cristata)", "bird", "Cyanocitta cristata", "Crested cobalt-blue corvid with black necklace; caches acorns and mimics Red-tailed Hawk calls."),
    ("american-crow", "American Crow (Corvus brachyrhynchos)", "bird", "Corvus brachyrhynchos", "All-black intelligent social corvid; squared fan tail and classic 'caw' (smaller than wedge-tailed Common Raven)."),
    ("black-capped-chickadee", "Black-capped Chickadee (Poecile atricapillus)", "bird", "Poecile atricapillus", "Black cap and bib, crisp white cheeks; caches thousands of seeds and grows its hippocampus each autumn."),
    ("tufted-titmouse", "Tufted Titmouse (Baeolophus bicolor)", "bird", "Baeolophus bicolor", "Mouse-gray songbird with pointed crest, big dark eyes, and peachy flanks; 'peter-peter-peter' call."),
    ("white-breasted-nuthatch", "White-breasted Nuthatch (Sitta carolinensis)", "bird", "Sitta carolinensis", "Blue-gray back, black cap, crisp white face; walks HEADFIRST down tree trunks probing bark crevices."),
    ("american-robin", "American Robin (Turdus migratorius)", "bird", "Turdus migratorius", "Large slate-backed thrush with warm brick-red breast; runs and pauses head-cocked on lawns listening for worms."),
    ("gray-catbird", "Gray Catbird (Dumetella carolinensis)", "bird", "Dumetella carolinensis", "Sleek all-slate songbird with black cap and chestnut undertail; unmistakable cat-like 'mew' from dense shrubs."),
    ("northern-mockingbird", "Northern Mockingbird (Mimus polyglottos)", "bird", "Mimus polyglottos", "Long-tailed gray mimic flashing bold white wing patches; repeats each imitated phrase 3+ times."),
    ("european-starling", "European Starling (Sturnus vulgaris)", "bird", "Sturnus vulgaris", "Iridescent purple-green glossy bird speckled with cream in winter; introduced to Central Park in 1890; forms murmurations."),
    ("cedar-waxwing", "Cedar Waxwing (Bombycilla cedrorum)", "bird", "Bombycilla cedrorum", "Silky fawn-brown crested fruit-eater with sleek black bandit mask, yellow tail tip, and red waxy wing dots."),
    ("yellow-warbler", "Yellow Warbler (Setophaga petechia)", "bird", "Setophaga petechia", "Sun-bright all-yellow spring migrant with rufous chest streaks on male; 'sweet-sweet-sweet, I'm so sweet!'."),
    ("northern-cardinal", "Northern Cardinal (Cardinalis cardinalis)", "bird", "Cardinalis cardinalis male", "Crested crimson male with black mask and heavy conical seed-cracking bill; year-round Northeast resident."),
    ("red-winged-blackbird", "Red-winged Blackbird (Agelaius phoeniceus)", "bird", "Agelaius phoeniceus male", "Jet-black marsh male flashing scarlet-and-yellow shoulder epaulets; 'conk-la-ree!' over cattails."),
    ("common-grackle", "Common Grackle (Quiscalus quiscula)", "bird", "Quiscalus quiscula", "Long keel-tailed blackbird with piercing yellow eye and iridescent bronze-purple head."),
    ("american-goldfinch", "American Goldfinch (Spinus tristis)", "bird", "Spinus tristis male", "Breeding male is electric lemon-yellow with black cap and wings; bouncy rollercoaster flight calling 'po-ta-to-chip'."),
    ("dark-eyed-junco", "Dark-eyed Junco (Junco hyemalis)", "bird", "Junco hyemalis", "Slate-gray hood/back, crisp white belly, pink bill, white outer tail feathers; classic Northeast winter 'snowbird'."),
    ("white-throated-sparrow", "White-throated Sparrow (Zonotrichia albicollis)", "bird", "Zonotrichia albicollis", "Bold black-and-white head stripes, bright yellow lore spot, crisp white throat; sings 'Old Sam Peabody'."),

    # ==================== CLOUDS & ATMOSPHERE (20) ====================
    ("cumulonimbus", "Cumulonimbus", "cloud", "Cumulonimbus anvil cloud", "Towering convective storm cloud reaching the tropopause with an ice-crystal anvil top; lightning & downpours."),
    ("cumulus-humilis", "Cumulus Humilis (Fair-Weather Cumulus)", "cloud", "Cumulus humilis", "Flat-bottomed puffy cotton clouds wider than tall; marks gentle daytime thermal convection and fair weather."),
    ("cumulus-congestus", "Cumulus Congestus (Towering Cumulus)", "cloud", "Cumulus congestus", "Cauliflower-topped tall convective towers growing vertically; immediate precursor to thunderstorm cells."),
    ("cirrus", "Cirrus", "cloud", "Cirrus clouds sky", "High-altitude (>6 km) wispy ice-crystal filaments ('mares' tails'); often precede a warm front by 12–24 h."),
    ("cirrostratus", "Cirrostratus", "cloud", "Cirrostratus halo", "Thin milky high-altitude ice veil covering the sky and producing a crisp 22° halo around the Sun or Moon."),
    ("cirrocumulus", "Cirrocumulus", "cloud", "Cirrocumulus", "High-altitude tiny rippled white cloudlets without shading ('fine mackerel sky'); indicates upper-level instability."),
    ("altocumulus", "Altocumulus", "cloud", "Altocumulus cloud", "Mid-level (2–6 km) dappled gray-white rolls or patches with shaded undersides; signals mid-level instability."),
    ("altostratus", "Altostratus", "cloud", "Altostratus", "Uniform blue-gray mid-level sheet dimming the Sun to a watery disk ('ground glass'); precedes steady rain."),
    ("stratus", "Stratus", "cloud", "Stratus clouds", "Low featureless gray blanket (<2 km) resembling elevated fog; brings mist or light drizzle."),
    ("stratocumulus", "Stratocumulus", "cloud", "Stratocumulus", "Low lumpy gray-white cellular layer with blue breaks; most common cloud type over Earth's oceans."),
    ("nimbostratus", "Nimbostratus", "cloud", "Nimbostratus", "Thick dark featureless low-to-mid rain deck completely blocking the Sun; steady multi-hour precipitation."),
    ("lenticular-cloud", "Altocumulus Lenticularis", "cloud", "Lenticular cloud", "Stationary lens-shaped standing wave cloud formed downwind of terrain; signals strong winds aloft and rotor turbulence."),
    ("mammatus-cloud", "Mammatus", "cloud", "Mammatus clouds", "Pouch-like cellular lobes hanging beneath a cumulonimbus anvil; formed by sinking cold moist air pockets."),
    ("kelvin-helmholtz-cloud", "Kelvin–Helmholtz Cloud (Fluctus)", "cloud", "Kelvin Helmholtz cloud", "Breaking-ocean-wave cloud curls formed by strong vertical wind shear between two air layers."),
    ("shelf-cloud", "Arcus / Shelf Cloud", "cloud", "Shelf cloud", "Low horizontal wedge attached to the leading edge of a thunderstorm outflow gust front; signals sudden wind surge."),
    ("virga", "Virga", "cloud", "Virga cloud", "Wispy streaks of rain or snow falling from a cloud base that evaporate before reaching dry ground."),
    ("sundog-parhelion", "Sundog (Parhelion)", "atmosphere", "Sun dog parhelion", "Bright rainbow-tinted light spots 22° left and right of the Sun, refracted by horizontally aligned hexagonal ice plates."),
    ("crepuscular-rays", "Crepuscular Rays", "atmosphere", "Crepuscular rays", "Parallel shafts of sunlight streaming through cloud gaps that appear to fan outward due to linear perspective."),
    ("alpenglow", "Belt of Venus / Alpenglow", "atmosphere", "Belt of Venus", "Pinkish-peach twilight arch above Earth's dark slate-blue shadow opposite the rising or setting Sun."),
    ("radiation-fog", "Radiation Valley Fog", "atmosphere", "Valley fog morning", "Clear calm nights let ground radiate heat away, cooling dense air below dew point into pooled valley fog."),

    # ==================== ROCKS, MINERALS & GEOLOGY (20) ====================
    ("manhattan-schist", "Mica Schist", "rock", "Mica schist rock", "Foliated metamorphic rock sparkling with platy muscovite/biotite mica; bedrock beneath Midtown and Downtown Manhattan."),
    ("granite", "Granite", "rock", "Granite rock close up", "Coarse-grained felsic intrusive igneous rock: interlocking quartz, pink/white feldspar, and dark biotite/hornblende."),
    ("basalt-columns", "Columnar Basalt", "rock", "Columnar basalt", "Fine-grained dark mafic volcanic rock; hexagonal cooling joints (like the Palisades diabase sill across the Hudson)."),
    ("gneiss", "Banded Gneiss", "rock", "Gneiss rock", "High-grade metamorphic rock with bold alternating light (quartz/feldspar) and dark (biotite/hornblende) mineral bands."),
    ("slate-rock", "Slate", "rock", "Slate rock", "Fine-grained low-grade metamorphic rock derived from shale; splits along crisp flat cleavage planes (roofing tile)."),
    ("marble-rock", "Marble", "rock", "Marble rock", "Metamorphosed limestone made of recrystallized interlocking calcite; soft (Mohs 3) and fizzes in weak acid."),
    ("quartzite", "Quartzite", "rock", "Quartzite rock", "Metamorphosed quartz sandstone fused so tightly it fractures cleanly across grains; ultra-hard (Mohs 7)."),
    ("sandstone", "Cross-Bedded Sandstone", "rock", "Cross bedding sandstone", "Clastic sedimentary rock of cemented sand grains; angled cross-beds preserve ancient dunes or river ripples."),
    ("limestone", "Fossiliferous Limestone", "rock", "Limestone rock", "Sedimentary rock mostly calcium carbonate (CaCO3) from marine shells/corals; forms karst caves and Portland cement."),
    ("shale-rock", "Shale", "rock", "Shale rock", "Fine-grained laminated mudstone sedimentary rock; splits in thin flakes; major hydrocarbon source rock."),
    ("conglomerate", "Conglomerate", "rock", "Conglomerate rock", "Sedimentary rock composed of rounded river/beach pebbles cemented in a finer matrix (angular clasts = breccia)."),
    ("obsidian", "Obsidian", "rock", "Obsidian rock", "Volcanic felsic glass cooled too fast for crystals; fractures with razor-sharp curved conchoidal ripples."),
    ("pumice", "Pumice", "rock", "Pumice stone", "Froth-filled vesicular volcanic glass full of trapped gas bubbles; low enough density (<1.0 g/cm³) to float on water."),
    ("quartz-crystal", "Quartz Crystal (SiO2)", "mineral", "Quartz crystal", "Hexagonal prismatic silicate crystal; Mohs hardness 7, glassy luster, conchoidal fracture, piezoelectric."),
    ("pyrite", "Pyrite (Fool's Gold, FeS2)", "mineral", "Pyrite cube", "Brassy metallic isometric cubes with striated faces; harder (Mohs 6–6.5) and lighter than gold, greenish-black streak."),
    ("feldspar", "Potassium Feldspar (Orthoclase)", "mineral", "Orthoclase feldspar", "Most abundant mineral group in Earth's crust (~60%); salmon-pink/white blocks with two clean 90° cleavage planes (Mohs 6)."),
    ("calcite", "Calcite (CaCO3)", "mineral", "Iceland spar calcite", "Rhombohedral carbonate crystal (Mohs 3) famous for optical double refraction and vigorous fizzing in acid."),
    ("muscovite-mica", "Muscovite Mica", "mineral", "Muscovite mica", "Silicate mineral with perfect basal cleavage peeling into flexible transparent silvery sheets."),
    ("glacial-erratic", "Glacial Erratic Boulder", "geology", "Glacial erratic Central Park", "Massive foreign boulder plucked and carried miles by Pleistocene ice sheets (ubiquitous across Central Park & Hudson Valley)."),
    ("glacial-striations", "Glacial Striations", "geology", "Glacial striations bedrock", "Parallel grooves scraped across exposed bedrock by rocks frozen into the base of advancing glaciers — shows ice flow direction."),

    # ==================== PLANTS, FUNGI, INSECTS & MAMMALS (25) ====================
    ("poison-ivy", "Poison Ivy (Toxicodendron radicans)", "plant", "Toxicodendron radicans leaf", "'Leaves of three, let it be'; shiny compound leaf with notched/mitten outer margins and hairy climbing vine; urushiol oil."),
    ("virginia-creeper", "Virginia Creeper (Parthenocissus quinquefolia)", "plant", "Parthenocissus quinquefolia", "Harmless native vine with FIVE leaflets (often confused with 3-leaf poison ivy); turns brilliant crimson in autumn."),
    ("staghorn-sumac", "Staghorn Sumac (Rhus typhina)", "plant", "Rhus typhina", "Fuzzy antler-like twigs, long ferny compound leaves, and upright velvety crimson berry cones along Northeast roadsides."),
    ("common-milkweed", "Common Milkweed (Asclepias syriaca)", "plant", "Asclepias syriaca", "Thick opposite leaves oozing white latex, dusty-pink star flower umbels, warty seed pods; sole host plant of Monarch caterpillars."),
    ("golden-rod", "Canada Goldenrod (Solidago canadensis)", "plant", "Solidago canadensis", "Plumed late-summer yellow wildflower pollinated by insects (NOT the cause of hay fever — wind-pollinated ragweed is)."),
    ("cattail", "Broadleaf Cattail (Typha latifolia)", "plant", "Typha latifolia", "Sword-like marsh blades topped by a dense velvety dark-brown cylindrical seed spike."),
    ("japanese-knotweed", "Japanese Knotweed (Reynoutria japonica)", "plant", "Reynoutria japonica", "Bamboo-like hollow speckled stems, spade-shaped leaves; notoriously aggressive invasive rhizome cracking foundations."),
    ("chicken-of-the-woods", "Chicken of the Woods (Laetiporus sulphureus)", "fungus", "Laetiporus sulphureus", "Bright sulfur-yellow and traffic-cone-orange overlapping shelf brackets on dead/dying oaks; choice edible polypore."),
    ("hen-of-the-woods", "Hen of the Woods / Maitake (Grifola frondosa)", "fungus", "Grifola frondosa", "Frilly gray-brown rosette of overlapping caps fruiting at the base of mature oaks in autumn."),
    ("turkey-tail", "Turkey Tail (Trametes versicolor)", "fungus", "Trametes versicolor", "Thin leathery fan brackets with concentric multicolored velvet zones and tiny white pores underneath; dead hardwood decomposer."),
    ("morel-mushroom", "Yellow Morel (Morchella esculenta)", "fungus", "Morchella esculenta", "Honeycomb-pitted sponge cap completely HOLLOW from cap tip to stem base; prized spring woodland fungus."),
    ("destroying-angel", "Destroying Angel (Amanita bisporigera)", "fungus", "Amanita bisporigera", "Pure ghostly white mushroom with cup-like basal volva, skirt ring, and white gills; contains lethal amatoxins."),
    ("giant-puffball", "Giant Puffball (Calvatia gigantea)", "fungus", "Calvatia gigantea", "Soccer-ball-sized white globe fruiting in late-summer meadows; solid marshmallow-white inside when young."),
    ("monarch-butterfly", "Monarch Butterfly (Danaus plexippus)", "insect", "Danaus plexippus", "Stained-glass orange wings with black veins and white-spotted borders; multi-generation 4,000 km migration to central Mexico."),
    ("eastern-tiger-swallowtail", "Eastern Tiger Swallowtail (Papilio glaucus)", "insect", "Papilio glaucus", "Large lemon-yellow butterfly with bold black tiger stripes and hindwing tails; common Northeast summer butterfly."),
    ("spotted-lanternfly", "Spotted Lanternfly (Lycorma delicatula)", "insect", "Lycorma delicatula", "Invasive planthopper with polka-dotted tan forewings and flash-scarlet hindwings; favors Tree of Heaven and grapes."),
    ("periodical-cicada", "Periodical Cicada (Magicicada)", "insect", "Magicicada", "Jet-black body, bulging ruby-red eyes, orange-veined wings; emerges synchronously every 13 or 17 years to swamp predators."),
    ("bald-faced-hornet", "Bald-faced Hornet (Dolichovespula maculata)", "insect", "Dolichovespula maculata", "Black-and-ivory aerial yellowjacket building basketball-sized gray paper nests hanging from tree limbs."),
    ("eastern-gray-squirrel", "Eastern Gray Squirrel (Sciurus carolinensis)", "mammal", "Sciurus carolinensis", "Bushy-tailed scatter-hoarding rodent; ankle joints rotate 180° to descend tree trunks headfirst."),
    ("eastern-chipmunk", "Eastern Chipmunk (Tamias striatus)", "mammal", "Tamias striatus", "Small russet ground squirrel with dark-white-dark dorsal stripes and expandable cheek pouches; digs deep winter burrows."),
    ("raccoon", "Raccoon (Procyon lotor)", "mammal", "Procyon lotor", "Black bandit mask, ringed tail, hyper-sensitive hairless forepaws whose tactile acuity doubles when wet."),
    ("virginia-opossum", "Virginia Opossum (Didelphis virginiana)", "mammal", "Didelphis virginiana", "North America's only marsupial; 50 teeth, prehensile tail, immune to most snake venom, eats thousands of ticks."),
    ("white-tailed-deer", "White-tailed Deer (Odocoileus virginianus)", "mammal", "Odocoileus virginianus", "Reddish-summer / gray-winter coat; flashes bright white underside of tail as an alarm flag when bounding."),
    ("red-fox", "Red Fox (Vulpes vulpes)", "mammal", "Vulpes vulpes", "Russet coat, black 'stocking' legs, white-tipped bushy tail; uses Earth's magnetic field to pounce on snow-buried voles."),
    ("eastern-cottontail", "Eastern Cottontail (Sylvilagus floridanus)", "mammal", "Sylvilagus floridanus", "Speckled brown-gray rabbit with rusty nape patch and powder-puff white tail; freezes motionless before zigzag sprinting."),
]

def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download_file(url: str, dest: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)

def search_commons_image(query: str):
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": 360,
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    for attempt in range(3):
        try:
            data = fetch_json(url)
            break
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5 * (attempt + 1))

    pages = data.get("query", {}).get("pages", {})
    ordered = sorted(pages.values(), key=lambda p: p.get("index", 999))
    for page in ordered:
        infos = page.get("imageinfo", [])
        if not infos:
            continue
        info = infos[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
        thumb = info.get("thumburl")
        desc_url = info.get("descriptionurl")
        if not thumb or not desc_url:
            continue
        meta = info.get("extmetadata", {})
        lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        artist = strip_html(meta.get("Artist", {}).get("value", "Unknown"))
        if len(artist) > 90:
            artist = artist[:87] + "..."
        if not any(pat in lic.lower() for pat in ALLOWED_LICENSE_PATTERNS):
            continue
        return {
            "thumburl": thumb,
            "source_url": desc_url,
            "license": lic,
            "artist": artist,
            "ext": "png" if mime == "image/png" else "jpg",
        }
    return None

def load_existing_cache():
    existing_log = os.path.join("content", "verification-natural-world.json")
    if not os.path.exists(existing_log):
        return {}
    try:
        rows = json.load(open(existing_log, "r", encoding="utf-8"))
        return {r["id"]: r for r in rows}
    except Exception:
        return {}

def process_specimen(spec, cache_map):
    slug, name, kind, query, desc = spec
    cid = f"nw-{slug}"
    if cid in cache_map:
        c = cache_map[cid]
        if os.path.exists(os.path.join("public", c["media"])):
            return (spec, {
                "media": c["media"],
                "source_url": c["source_url"],
                "license": c["license"],
                "artist": c["artist"],
                "cached": True,
            })

    found = search_commons_image(query)
    if not found:
        return (spec, None)

    filename = f"{slug}.{found['ext']}"
    rel_media = f"media/natural-world/{filename}"
    dest_path = os.path.join("public", rel_media)
    if not os.path.exists(dest_path):
        for attempt in range(3):
            try:
                download_file(found["thumburl"], dest_path)
                break
            except Exception:
                if attempt == 2:
                    return (spec, None)
                time.sleep(1.5 * (attempt + 1))

    return (spec, {
        "media": rel_media,
        "source_url": found["source_url"],
        "license": found["license"],
        "artist": found["artist"],
        "cached": False,
    })

def main():
    media_dir = os.path.join("public", "media", "natural-world")
    os.makedirs(media_dir, exist_ok=True)
    cache_map = load_existing_cache()

    results = {}
    failed = []
    # Polite concurrency (3 workers) to respect Wikimedia Commons limits
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(process_specimen, spec, cache_map): spec[0] for spec in SPECIMENS}
        done = 0
        for fut in as_completed(futs):
            spec, info = fut.result()
            done += 1
            if info:
                results[spec[0]] = (spec, info)
            else:
                failed.append(spec[0])
            if done % 20 == 0 or done == len(SPECIMENS):
                print(f"Natural World Commons progress: {done}/{len(SPECIMENS)} (ok={len(results)}, failed={len(failed)})")

    entities = []
    plain_cards = []
    verification_log = []

    for spec in SPECIMENS:
        slug = spec[0]
        if slug not in results:
            continue
        (_, name, kind, _, desc), info = results[slug]
        entities.append({
            "id": slug,
            "name": name,
            "kind": kind,
            "module": "natural_world",
            "tags": ["northeast", "nyc", kind],
        })
        plain_cards.append({
            "id": f"nw-{slug}",
            "module": "natural_world",
            "entity_id": slug,
            "tags": ["northeast", kind],
            "front": f"Identify this {kind}",
            "back": f"{name} — {desc}",
            "media": info["media"],
            "attribution": f"{info['artist']} · {info['license']} (Wikimedia Commons)",
            "source_url": info["source_url"],
            "source_note": f"Wikimedia Commons openly licensed photograph ({info['license']})",
            "as_of": str(date.today()),
            "volatile": False,
        })
        verification_log.append({
            "id": f"nw-{slug}",
            "source_url": info["source_url"],
            "license": info["license"],
            "artist": info["artist"],
            "media": info["media"],
        })

    pack = {
        "pack_id": "natural-world-northeast",
        "version": "0.2.0",
        "release_date": str(date.today()),
        "module": "natural_world",
        "entities": entities,
        "dimensions": [],
        "facts": [],
        "anchor_sets": [],
        "figures": [],
        "plain_cards": plain_cards,
    }

    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "natural_world.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join("content", "verification-natural-world.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote M3 natural_world.json: {len(plain_cards)} verified offline visual cards (skipped/failed: {failed}).")

if __name__ == "__main__":
    main()
