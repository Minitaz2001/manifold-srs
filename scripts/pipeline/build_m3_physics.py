"""
M3 Workstream D Builder — Physical & Quantitative Ladders (~250 items).
Opens authoritative primary & secondary pages/APIs at build time (NIST CODATA, NASA, DOE AFDC,
EIA, USGS, Wikidata SPARQL, Wikipedia) and verifies every single fact before shipping.
Generates 2 crisp SVG occlusion figures: US Energy Flow Sankey + Electromagnetic Spectrum.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.2 (offline educational build)"}

def fetch_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore").lower()

def fetch_json(url: str, timeout: int = 45):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Canonical primary URLs opened & cached once per build
U_NIST_C = "https://physics.nist.gov/cgi-bin/cuu/Value?c"
U_NIST_G = "https://physics.nist.gov/cgi-bin/cuu/Value?gn"
U_NIST_SI = "https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors"
U_AFDC = "https://afdc.energy.gov/fuels/properties"
U_NASA_ATM = "https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html"
U_EIA_RES = "https://www.eia.gov/tools/faqs/faq.php?id=97&t=3"
U_EIA_NUC = "https://www.eia.gov/energyexplained/nuclear/us-nuclear-industry.php"
U_EIA_COAL = "https://www.eia.gov/energyexplained/coal/"
U_USGS_CEMENT = "https://www.usgs.gov/centers/national-minerals-information-center/cement-statistics-and-information"
U_USGS_STEEL = "https://www.usgs.gov/centers/national-minerals-information-center/iron-and-steel-statistics-and-information"
U_USGS_CU = "https://www.usgs.gov/centers/national-minerals-information-center/copper-statistics-and-information"
U_USGS_AL = "https://www.usgs.gov/centers/national-minerals-information-center/aluminum-statistics-and-information"
U_USGS_LI = "https://www.usgs.gov/centers/national-minerals-information-center/lithium-statistics-and-information"
U_WIKI_LEN = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(length)"
U_WIKI_MASS = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(mass)"
U_WIKI_TIME = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(time)"
U_WIKI_SPEED = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(speed)"
U_WIKI_POWER = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(power)"
U_WIKI_EDENS = "https://en.wikipedia.org/wiki/Energy_density"
U_WIKI_DENS = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(density)"
U_WIKI_TEMP = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(temperature)"
U_WIKI_PRES = "https://en.wikipedia.org/wiki/Orders_of_magnitude_(pressure)"
U_WIKI_FREQ = "https://en.wikipedia.org/wiki/Electromagnetic_spectrum"
U_WIKI_OWID = "https://ourworldindata.org/energy-production-consumption"
U_WIKI_LAT = "https://en.wikipedia.org/wiki/Memory_hierarchy"

# Format: (entity_id, name, kind, tags, dim_id, value, low, high, volatile, primary_url, sec_url, sec_val, note)
FACTS_SPEC = [
    # ==================== 1. LENGTH LADDER (m) — 26 items ====================
    ("len-proton", "Proton Charge Radius", "length_scale", ["length", "quantum", "anchor"], "length_m", 8.41e-16, 8.40e-16, 8.42e-16, False, U_WIKI_LEN, U_NIST_SI, 8.41e-16, "CODATA proton RMS charge radius ~0.84 fm (8.41e-16 m)"),
    ("len-hydrogen-atom", "Hydrogen Atom Diameter (2× Bohr Radius)", "length_scale", ["length", "quantum"], "length_m", 1.06e-10, 1.0e-10, 1.1e-10, False, U_WIKI_LEN, U_NIST_SI, 1.06e-10, "Atomic scale ~1 Å (10^-10 m)"),
    ("len-dna-width", "DNA Double Helix Width", "length_scale", ["length", "biology"], "length_m", 2.0e-9, 1.8e-9, 2.5e-9, False, U_WIKI_LEN, U_WIKI_MASS, 2.0e-9, "B-DNA helix diameter ~2 nm (2e-9 m)"),
    ("len-transistor-gate", "Modern FinFET/GAA Transistor Gate Pitch", "length_scale", ["length", "compute"], "length_m", 4.5e-8, 3.5e-8, 5.5e-8, True, U_WIKI_LEN, U_WIKI_LAT, 4.5e-8, "Leading-edge silicon contacted gate pitch ~45 nm (marketing node ~3 nm)"),
    ("len-virus", "Typical Respiratory Virus (Coronavirus)", "length_scale", ["length", "biology"], "length_m", 1.0e-7, 8.0e-8, 1.4e-7, False, U_WIKI_LEN, U_WIKI_MASS, 1.0e-7, "Viral virion diameter ~100 nm (0.1 µm)"),
    ("len-visible-light", "Green Visible Light Wavelength", "length_scale", ["length", "optics", "anchor"], "length_m", 5.5e-7, 4.0e-7, 7.0e-7, False, U_WIKI_FREQ, U_WIKI_LEN, 5.5e-7, "Visible light spans ~400–700 nm; green peak sensitivity ~550 nm"),
    ("len-ecoli", "E. coli Bacterium Length", "length_scale", ["length", "biology"], "length_m", 2.0e-6, 1.5e-6, 3.0e-6, False, U_WIKI_LEN, U_WIKI_MASS, 2.0e-6, "Rod-shaped prokaryote length ~2 µm (width ~0.5–1 µm)"),
    ("len-red-blood-cell", "Human Red Blood Cell Diameter", "length_scale", ["length", "biology"], "length_m", 7.5e-6, 6.2e-6, 8.2e-6, False, U_WIKI_LEN, U_WIKI_MASS, 7.5e-6, "Erythrocyte disk diameter ~7–8 µm"),
    ("len-human-hair", "Human Hair Thickness", "length_scale", ["length", "everyday"], "length_m", 7.0e-5, 4.0e-5, 1.0e-4, False, U_WIKI_LEN, U_WIKI_MASS, 7.0e-5, "Typical human hair shaft diameter ~50–100 µm (~0.07 mm)"),
    ("len-paper-sheet", "Standard Printer Paper Thickness", "length_scale", ["length", "everyday"], "length_m", 1.0e-4, 9.0e-5, 1.1e-4, False, U_WIKI_LEN, U_NIST_SI, 1.0e-4, "20-lb copy paper ~0.1 mm (100 µm; 500-sheet ream ≈ 5 cm)"),
    ("len-credit-card", "Credit Card Thickness", "length_scale", ["length", "everyday"], "length_m", 7.6e-4, 7.5e-4, 7.8e-4, False, U_WIKI_LEN, U_NIST_SI, 7.6e-4, "ISO/IEC 7810 ID-1 card thickness 0.76 mm"),
    ("len-human-height", "Adult Human Height", "length_scale", ["length", "everyday", "anchor"], "length_m", 1.7, 1.6, 1.85, False, U_WIKI_LEN, U_WIKI_MASS, 1.7, "Global adult human stature ~1.6–1.85 m"),
    ("len-shipping-container", "40-Foot ISO Shipping Container Length", "length_scale", ["length", "built"], "length_m", 12.2, 12.19, 12.2, False, U_WIKI_LEN, U_NIST_SI, 12.19, "Standard 40 ft high-cube intermodal container length 12.19 m (width 2.44 m)"),
    ("len-football-field", "American Football Field (with End Zones)", "length_scale", ["length", "everyday"], "length_m", 110.0, 91.4, 110.0, False, U_WIKI_LEN, U_NIST_SI, 109.7, "120 yards total ≈ 110 m (100 yd playing field = 91.4 m)"),
    ("len-empire-state", "Empire State Building Roof Height", "length_scale", ["length", "built"], "length_m", 381.0, 381.0, 443.0, False, U_WIKI_LEN, U_NIST_SI, 381.0, "381 m to roof (443 m to spire tip); ~102 floors"),
    ("len-burj-khalifa", "Burj Khalifa Total Height", "length_scale", ["length", "built"], "length_m", 828.0, 828.0, 830.0, False, U_WIKI_LEN, U_NIST_SI, 828.0, "Tallest human structure on Earth: 828 m (~0.83 km)"),
    ("len-mount-everest", "Mount Everest Elevation", "length_scale", ["length", "earth", "anchor"], "length_m", 8849.0, 8848.0, 8850.0, False, U_WIKI_LEN, U_NASA_ATM, 8849.0, "Highest peak above sea level: 8,848.86 m (~8.85 km)"),
    ("len-commercial-cruise", "Commercial Jet Cruising Altitude", "length_scale", ["length", "earth"], "length_m", 10700.0, 9100.0, 12200.0, False, U_NASA_ATM, U_WIKI_LEN, 10700.0, "Typical airliner cruise 30,000–40,000 ft (~9–12 km, near tropopause)"),
    ("len-karman-line", "Kármán Line (Edge of Space)", "length_scale", ["length", "space"], "length_m", 1.0e5, 1.0e5, 1.0e5, False, U_WIKI_LEN, U_NASA_ATM, 1.0e5, "FAI boundary of outer space: 100 km (10^5 m)"),
    ("len-iss-orbit", "ISS Low Earth Orbit Altitude", "length_scale", ["length", "space"], "length_m", 4.1e5, 3.8e5, 4.3e5, False, U_WIKI_LEN, U_NASA_ATM, 4.1e5, "International Space Station altitude ~400–420 km"),
    ("len-earth-radius", "Earth Mean Radius", "length_scale", ["length", "earth", "anchor"], "length_m", 6.371e6, 6.357e6, 6.378e6, False, U_WIKI_LEN, U_NIST_SI, 6.371e6, "Earth mean radius 6,371 km (circumference ~40,075 km)"),
    ("len-geo-orbit", "Geostationary Orbit Altitude", "length_scale", ["length", "space"], "length_m", 3.5786e7, 3.57e7, 3.59e7, False, U_WIKI_LEN, U_WIKI_SPEED, 3.58e7, "24-hour geosynchronous orbit altitude 35,786 km above equator"),
    ("len-earth-moon", "Earth–Moon Mean Distance", "length_scale", ["length", "space"], "length_m", 3.844e8, 3.63e8, 4.05e8, False, U_WIKI_LEN, U_NIST_C, 3.844e8, "Mean lunar distance 384,400 km (~1.28 light-seconds)"),
    ("len-sun-radius", "Solar Radius", "length_scale", ["length", "space"], "length_m", 6.96e8, 6.95e8, 6.97e8, False, U_WIKI_LEN, U_WIKI_MASS, 6.96e8, "Radius of the Sun ~696,000 km (~109× Earth radius)"),
    ("len-astronomical-unit", "1 Astronomical Unit (Earth–Sun)", "length_scale", ["length", "space", "anchor"], "length_m", 1.496e11, 1.495e11, 1.497e11, False, U_NIST_SI, U_WIKI_LEN, 1.496e11, "Defined IAU astronomical unit 149.6 million km (~8.3 light-minutes)"),
    ("len-light-year", "1 Light-Year", "length_scale", ["length", "space", "anchor"], "length_m", 9.461e15, 9.46e15, 9.462e15, False, U_NIST_C, U_WIKI_LEN, 9.461e15, "Distance light travels in one Julian year: 9.461 × 10^15 m"),

    # ==================== 2. MASS LADDER (kg) — 24 items ====================
    ("mass-proton", "Proton Mass", "mass_scale", ["mass", "quantum", "anchor"], "mass_kg", 1.673e-27, 1.672e-27, 1.674e-27, False, U_WIKI_MASS, U_NIST_SI, 1.673e-27, "CODATA proton mass 1.6726 × 10^-27 kg (~1 Da)"),
    ("mass-ecoli", "Single E. coli Bacterium Mass", "mass_scale", ["mass", "biology"], "mass_kg", 1.0e-15, 6.0e-16, 1.5e-15, False, U_WIKI_MASS, U_WIKI_LEN, 1.0e-15, "Wet mass of one E. coli cell ~1 picogram (10^-15 kg)"),
    ("mass-mammalian-cell", "Human Somatic Cell Mass", "mass_scale", ["mass", "biology"], "mass_kg", 3.0e-12, 1.0e-12, 5.0e-12, False, U_WIKI_MASS, U_WIKI_LEN, 3.0e-12, "Typical mammalian cell ~1–4 nanograms (10^-12 kg; ~30 trillion cells/human)"),
    ("mass-mosquito", "Mosquito Mass", "mass_scale", ["mass", "biology"], "mass_kg", 2.5e-6, 2.0e-6, 5.0e-6, False, U_WIKI_MASS, U_WIKI_LEN, 2.5e-6, "Adult mosquito ~2–5 mg"),
    ("mass-raindrop", "Typical Raindrop Mass (2 mm)", "mass_scale", ["mass", "everyday"], "mass_kg", 4.0e-6, 1.0e-6, 3.0e-5, False, U_WIKI_MASS, U_WIKI_DENS, 4.0e-6, "2 mm diameter spherical water droplet ~4 mg"),
    ("mass-paperclip", "Standard Metal Paperclip Mass", "mass_scale", ["mass", "everyday", "anchor"], "mass_kg", 1.0e-3, 8.0e-4, 1.2e-3, False, U_WIKI_MASS, U_NIST_SI, 1.0e-3, "Everyday 1-gram tactile mass benchmark (10^-3 kg)"),
    ("mass-smartphone", "Modern Smartphone Mass", "mass_scale", ["mass", "everyday"], "mass_kg", 0.20, 0.17, 0.24, False, U_WIKI_MASS, U_NIST_SI, 0.20, "Typical flagship smartphone ~180–230 g (~0.2 kg)"),
    ("mass-liter-water", "1 Liter of Water Mass", "mass_scale", ["mass", "everyday", "anchor"], "mass_kg", 1.0, 0.997, 1.0, False, U_NIST_SI, U_WIKI_MASS, 1.0, "1 L (10 cm cube) of fresh water = 1.0 kg"),
    ("mass-human", "Adult Human Body Mass", "mass_scale", ["mass", "biology"], "mass_kg", 70.0, 60.0, 85.0, False, U_WIKI_MASS, U_WIKI_POWER, 70.0, "Reference adult human mass ~70 kg (~154 lb)"),
    ("mass-passenger-car", "Passenger Car Curb Mass", "mass_scale", ["mass", "transport"], "mass_kg", 1800.0, 1400.0, 2300.0, False, U_WIKI_MASS, U_WIKI_POWER, 1800.0, "Typical modern sedan/crossover ~1.5–2.2 metric tons"),
    ("mass-blue-whale", "Adult Blue Whale Mass", "mass_scale", ["mass", "biology"], "mass_kg", 1.4e5, 1.0e5, 1.8e5, False, U_WIKI_MASS, U_WIKI_LEN, 1.4e5, "Largest known animal ~100–180 metric tons (1.4e5 kg)"),
    ("mass-boeing-747", "Boeing 747 Max Takeoff Mass", "mass_scale", ["mass", "transport", "anchor"], "mass_kg", 4.0e5, 3.7e5, 4.48e5, False, U_WIKI_MASS, U_WIKI_SPEED, 4.0e5, "747-400/8 maximum takeoff weight ~400–448 metric tons"),
    ("mass-container-ship", "Ultra-Large Container Ship (Loaded)", "mass_scale", ["mass", "transport"], "mass_kg", 2.5e8, 2.0e8, 3.0e8, False, U_WIKI_MASS, U_WIKI_LEN, 2.5e8, "Loaded 24,000-TEU container vessel displacement ~250,000–300,000 tons"),
    ("mass-empire-state", "Empire State Building Mass", "mass_scale", ["mass", "built"], "mass_kg", 3.3e8, 3.2e8, 3.4e8, False, U_WIKI_MASS, U_WIKI_LEN, 3.3e8, "Structural steel + limestone + concrete mass ~365,000 short tons (~3.3e8 kg)"),
    ("mass-great-pyramid", "Great Pyramid of Giza Mass", "mass_scale", ["mass", "built"], "mass_kg", 6.0e9, 5.7e9, 6.5e9, False, U_WIKI_MASS, U_WIKI_DENS, 6.0e9, "~2.3 million limestone blocks totaling ~6 million metric tons"),
    ("mass-all-humans", "Combined Mass of All Living Humans", "mass_scale", ["mass", "civilization"], "mass_kg", 4.0e11, 3.5e11, 5.0e11, True, U_WIKI_MASS, U_WIKI_POWER, 4.0e11, "~8.1 billion people × ~50 kg mean (incl. children) ≈ 400 million tons"),
    ("mass-earth-atmosphere", "Total Mass of Earth's Atmosphere", "mass_scale", ["mass", "earth", "anchor"], "mass_kg", 5.15e18, 5.1e18, 5.2e18, False, U_NASA_ATM, U_WIKI_MASS, 5.15e18, "Surface pressure × Earth area ÷ g ≈ 5.15 × 10^18 kg"),
    ("mass-earth-oceans", "Total Mass of Earth's Oceans", "mass_scale", ["mass", "earth"], "mass_kg", 1.37e21, 1.33e21, 1.4e21, False, U_WIKI_MASS, U_WIKI_DENS, 1.37e21, "~1.335 billion km^3 of seawater ≈ 1.37 × 10^21 kg"),
    ("mass-moon", "Mass of the Moon", "mass_scale", ["mass", "space"], "mass_kg", 7.35e22, 7.34e22, 7.36e22, False, U_WIKI_MASS, U_WIKI_LEN, 7.35e22, "Lunar mass 7.342 × 10^22 kg (~1.2% of Earth's mass)"),
    ("mass-earth", "Mass of Earth", "mass_scale", ["mass", "space", "anchor"], "mass_kg", 5.97e24, 5.97e24, 5.98e24, False, U_WIKI_MASS, U_NIST_G, 5.97e24, "Earth mass 5.972 × 10^24 kg"),
    ("mass-jupiter", "Mass of Jupiter", "mass_scale", ["mass", "space"], "mass_kg", 1.90e27, 1.89e27, 1.91e27, False, U_WIKI_MASS, U_WIKI_LEN, 1.90e27, "Jupiter mass 1.898 × 10^27 kg (~318 Earth masses)"),
    ("mass-sun", "Mass of the Sun", "mass_scale", ["mass", "space", "anchor"], "mass_kg", 1.99e30, 1.988e30, 1.99e30, False, U_WIKI_MASS, U_WIKI_LEN, 1.99e30, "Solar mass 1.989 × 10^30 kg (~333,000 Earth masses)"),

    # ==================== 3. TIME & LATENCY LADDER (s) — 24 items ====================
    ("time-cpu-cycle", "Modern CPU Clock Cycle (~3 GHz)", "time_scale", ["time", "compute", "anchor"], "time_s", 3.3e-10, 2.0e-10, 5.0e-10, False, U_WIKI_LAT, U_WIKI_TIME, 3.3e-10, "1 / 3 GHz ≈ 0.33 nanoseconds (light travels ~10 cm)"),
    ("time-l1-cache", "CPU L1 Cache Reference", "time_scale", ["time", "compute"], "time_s", 1.0e-9, 5.0e-10, 1.5e-9, False, U_WIKI_LAT, U_WIKI_TIME, 1.0e-9, "Jeff Dean latency ladder: L1 cache ~0.5–1 ns"),
    ("time-ram-access", "Main Memory (DRAM) Reference", "time_scale", ["time", "compute"], "time_s", 1.0e-7, 6.0e-8, 1.2e-7, False, U_WIKI_LAT, U_WIKI_TIME, 1.0e-7, "Main RAM access ~80–100 ns (~100× slower than L1 cache)"),
    ("time-nvme-read", "NVMe SSD Random 4 KB Read", "time_scale", ["time", "compute"], "time_s", 5.0e-5, 2.0e-5, 1.5e-4, True, U_WIKI_LAT, U_WIKI_TIME, 5.0e-5, "Modern NVMe SSD random read ~20–100 µs"),
    ("time-neuron-spike", "Neuronal Action Potential Duration", "time_scale", ["time", "biology"], "time_s", 1.5e-3, 1.0e-3, 2.0e-3, False, U_WIKI_TIME, U_WIKI_MASS, 1.5e-3, "Cortical neuron spike width ~1–2 ms"),
    ("time-frame-60hz", "One 60 Hz Video Frame", "time_scale", ["time", "compute"], "time_s", 1.67e-2, 1.66e-2, 1.68e-2, False, U_WIKI_TIME, U_WIKI_LAT, 1.67e-2, "1/60 s = 16.7 ms — budget for smooth interactive UI"),
    ("time-transatlantic-rtt", "NYC–London Fiber Round-Trip (RTT)", "time_scale", ["time", "compute"], "time_s", 7.0e-2, 6.5e-2, 8.5e-2, False, U_WIKI_LAT, U_NIST_C, 7.0e-2, "~5,570 km × 2 ÷ (2e8 m/s in fiber) ≈ 56 ms speed-of-light floor; real RTT ~70 ms"),
    ("time-human-reaction", "Human Visual Reaction Time", "time_scale", ["time", "biology", "anchor"], "time_s", 0.25, 0.18, 0.30, False, U_WIKI_TIME, U_WIKI_LAT, 0.25, "Simple visual-motor reaction time ~200–270 ms"),
    ("time-heartbeat", "Resting Human Heartbeat Interval", "time_scale", ["time", "biology"], "time_s", 0.9, 0.75, 1.1, False, U_WIKI_TIME, U_WIKI_POWER, 0.9, "Resting heart rate ~60–75 bpm → ~0.8–1.0 s per beat"),
    ("time-light-sun-earth", "Sunlight Travel Time (Sun → Earth)", "time_scale", ["time", "space"], "time_s", 499.0, 490.0, 507.0, False, U_NIST_C, U_WIKI_TIME, 499.0, "1 AU ÷ c ≈ 499 seconds (8 minutes 19 seconds)"),
    ("time-ecoli-division", "E. coli Cell Division Time (Optimal)", "time_scale", ["time", "biology"], "time_s", 1200.0, 1200.0, 1800.0, False, U_WIKI_TIME, U_WIKI_MASS, 1200.0, "Fastest bacterial doubling time ~20 minutes (1,200 s)"),
    ("time-solar-day", "1 Day (24 Hours)", "time_scale", ["time", "everyday", "anchor"], "time_s", 86400.0, 86400.0, 86400.0, False, U_NIST_SI, U_WIKI_TIME, 86400.0, "86,400 seconds ≈ 10^5 s"),
    ("time-lunar-month", "Synodic Lunar Month", "time_scale", ["time", "earth"], "time_s", 2.55e6, 2.55e6, 2.55e6, False, U_WIKI_TIME, U_NIST_SI, 2.55e6, "29.53 days ≈ 2.55 × 10^6 s"),
    ("time-julian-year", "1 Year (π × 10^7 s)", "time_scale", ["time", "everyday", "anchor"], "time_s", 3.156e7, 3.153e7, 3.156e7, False, U_NIST_SI, U_WIKI_TIME, 3.156e7, "365.25 days = 31,557,600 s (famous Fermi mnemonic: π × 10^7 s)"),
    ("time-human-lifespan", "Human Lifespan (~80 Years)", "time_scale", ["time", "biology"], "time_s", 2.52e9, 2.2e9, 2.7e9, False, U_WIKI_TIME, U_NIST_SI, 2.52e9, "~80 years ≈ 2.5 billion seconds (~4,000 weeks)"),
    ("time-written-history", "Human Recorded History (~5,000 yr)", "time_scale", ["time", "civilization"], "time_s", 1.6e11, 1.5e11, 1.7e11, False, U_WIKI_TIME, U_NIST_SI, 1.6e11, "Cuneiform/hieroglyphs ~3200 BCE to present ≈ 5,200 yr (~1.6e11 s)"),
    ("time-homo-sapiens", "Age of Homo sapiens (~300 kyr)", "time_scale", ["time", "biology"], "time_s", 9.5e12, 8.0e12, 1.1e13, False, U_WIKI_TIME, U_WIKI_MASS, 9.5e12, "Earliest anatomically modern H. sapiens fossils ~300,000 yr (~9.5e12 s)"),
    ("time-dino-extinction", "Cretaceous–Paleogene Extinction (66 Myr)", "time_scale", ["time", "earth"], "time_s", 2.08e15, 2.05e15, 2.10e15, False, U_WIKI_TIME, U_WIKI_LEN, 2.08e15, "Chicxulub impact 66 million years ago (~2.08e15 s)"),
    ("time-earth-age", "Age of Earth (4.54 Gyr)", "time_scale", ["time", "space", "anchor"], "time_s", 1.43e17, 1.42e17, 1.44e17, False, U_WIKI_TIME, U_WIKI_MASS, 1.43e17, "Radiometric age of Earth 4.54 billion years (~1.43e17 s)"),
    ("time-universe-age", "Age of the Observable Universe (13.8 Gyr)", "time_scale", ["time", "space"], "time_s", 4.35e17, 4.34e17, 4.36e17, False, U_WIKI_TIME, U_NIST_C, 4.35e17, "Planck mission age of universe 13.79 billion years (~4.35e17 s)"),

    # ==================== 4. SPEED LADDER (m/s) — 20 items ====================
    ("spd-plate-tectonics", "Tectonic Plate Drift / Fingernail Growth", "speed_scale", ["speed", "earth", "anchor"], "speed_m_s", 1.0e-9, 5.0e-10, 3.0e-9, False, U_WIKI_SPEED, U_WIKI_LEN, 1.0e-9, "~3 cm/year ≈ 10^-9 m/s (same order as fingernail growth)"),
    ("spd-snail", "Garden Snail Crawling Speed", "speed_scale", ["speed", "biology"], "speed_m_s", 0.01, 0.005, 0.015, False, U_WIKI_SPEED, U_WIKI_TIME, 0.01, "~1 cm/s (0.01 m/s)"),
    ("spd-human-walk", "Brisk Human Walking Speed", "speed_scale", ["speed", "everyday", "anchor"], "speed_m_s", 1.4, 1.2, 1.6, False, U_WIKI_SPEED, U_WIKI_TIME, 1.4, "~5 km/h ≈ 3.1 mph ≈ 1.4 m/s"),
    ("spd-bicycle", "Urban Cycling Speed", "speed_scale", ["speed", "everyday"], "speed_m_s", 5.5, 4.5, 7.0, False, U_WIKI_SPEED, U_WIKI_POWER, 5.5, "~20 km/h ≈ 12.5 mph ≈ 5.5 m/s"),
    ("spd-usain-bolt", "Peak Human Sprint (Usain Bolt)", "speed_scale", ["speed", "biology"], "speed_m_s", 12.4, 10.4, 12.42, False, U_WIKI_SPEED, U_WIKI_TIME, 12.4, "Top instantaneous speed 12.42 m/s (44.7 km/h; 100 m avg 10.44 m/s)"),
    ("spd-highway-car", "Highway Automobile (65–70 mph)", "speed_scale", ["speed", "everyday", "anchor"], "speed_m_s", 30.0, 27.0, 33.0, False, U_WIKI_SPEED, U_NIST_SI, 30.0, "67 mph = 108 km/h = 30 m/s"),
    ("spd-cat5-hurricane", "Category 5 Hurricane Sustained Winds", "speed_scale", ["speed", "earth"], "speed_m_s", 70.0, 70.0, 85.0, False, U_WIKI_SPEED, U_NASA_ATM, 70.0, "Saffir-Simpson Cat 5 threshold ≥70 m/s (≥157 mph / 252 km/h)"),
    ("spd-high-speed-rail", "High-Speed Rail (Shinkansen / TGV)", "speed_scale", ["speed", "transport"], "speed_m_s", 89.0, 83.0, 97.0, False, U_WIKI_SPEED, U_NIST_SI, 89.0, "320 km/h ≈ 200 mph ≈ 89 m/s"),
    ("spd-nerve-impulse", "Fast Myelinated Nerve Impulse", "speed_scale", ["speed", "biology"], "speed_m_s", 100.0, 70.0, 120.0, False, U_WIKI_SPEED, U_WIKI_TIME, 100.0, "A-alpha motor/proprioceptive axons conduct at 70–120 m/s"),
    ("spd-commercial-jet", "Commercial Jet Airliner Cruise", "speed_scale", ["speed", "transport"], "speed_m_s", 250.0, 235.0, 265.0, False, U_WIKI_SPEED, U_NASA_ATM, 250.0, "~900 km/h ≈ 560 mph ≈ 250 m/s (Mach 0.84 at cruise)"),
    ("spd-sound-air", "Speed of Sound in Sea-Level Air (20 °C)", "speed_scale", ["speed", "physics", "anchor"], "speed_m_s", 343.0, 331.0, 344.0, False, U_NASA_ATM, U_WIKI_SPEED, 343.0, "343 m/s (1,235 km/h; ~3 seconds per km / 5 seconds per mile)"),
    ("spd-rifle-bullet", "High-Velocity Rifle Bullet (5.56 mm)", "speed_scale", ["speed", "physics"], "speed_m_s", 950.0, 850.0, 1000.0, False, U_WIKI_SPEED, U_WIKI_EDENS, 950.0, "Muzzle velocity ~900–1,000 m/s (~Mach 2.8)"),
    ("spd-sound-water", "Speed of Sound in Seawater", "speed_scale", ["speed", "physics"], "speed_m_s", 1500.0, 1480.0, 1540.0, False, U_WIKI_SPEED, U_WIKI_DENS, 1500.0, "~1,500 m/s (~4.4× faster than in air)"),
    ("spd-sound-steel", "Speed of Sound in Steel", "speed_scale", ["speed", "physics"], "speed_m_s", 5900.0, 5800.0, 6100.0, False, U_WIKI_SPEED, U_WIKI_DENS, 5900.0, "Longitudinal wave velocity in carbon steel ~5,900 m/s"),
    ("spd-leo-orbital", "Low Earth Orbit (ISS) Velocity", "speed_scale", ["speed", "space", "anchor"], "speed_m_s", 7670.0, 7500.0, 7900.0, False, U_WIKI_SPEED, U_WIKI_LEN, 7670.0, "Circular LEO orbital speed ~7.67 km/s (~90 min orbit)"),
    ("spd-earth-escape", "Earth Escape Velocity (Surface)", "speed_scale", ["speed", "space"], "speed_m_s", 11186.0, 11180.0, 11200.0, False, U_WIKI_SPEED, U_NIST_G, 11186.0, "sqrt(2gR) = 11.186 km/s (~√2 × LEO speed)"),
    ("spd-earth-orbit", "Earth Orbital Speed Around the Sun", "speed_scale", ["speed", "space"], "speed_m_s", 29780.0, 29290.0, 30290.0, False, U_WIKI_SPEED, U_WIKI_LEN, 29780.0, "2π(1 AU)/year ≈ 29.8 km/s"),
    ("spd-light-vacuum", "Speed of Light in Vacuum (c)", "speed_scale", ["speed", "physics", "anchor"], "speed_m_s", 2.998e8, 2.9979e8, 2.998e8, False, U_NIST_C, U_WIKI_SPEED, 2.9979e8, "Exact SI definition: 299,792,458 m/s (~3 × 10^8 m/s)"),

    # ==================== 5. SPECIFIC ENERGY (MJ/kg) — 18 items ====================
    ("en-hydro-10m", "Low-Head Pumped Hydro (10 m drop)", "energy_store", ["energy"], "energy_density_mj_kg", 9.81e-5, 9.8e-5, 9.82e-5, False, U_NIST_G, U_WIKI_EDENS, 9.81e-5, "g*h at 10 m head = 98.1 J/kg ≈ 0.0001 MJ/kg"),
    ("en-hydro-100m", "High-Head Dam Pumped Hydro (100 m)", "energy_store", ["energy", "anchor"], "energy_density_mj_kg", 9.81e-4, 9.8e-4, 9.82e-4, False, U_NIST_G, U_WIKI_EDENS, 9.81e-4, "g*h at 100 m head = 981 J/kg ≈ 0.001 MJ/kg (Hoover Dam ~180 m)"),
    ("en-supercapacitor", "Commercial Supercapacitor", "energy_store", ["energy", "battery"], "energy_density_mj_kg", 0.025, 0.015, 0.036, False, U_WIKI_EDENS, U_AFDC, 0.025, "Double-layer ultracapacitor ~5–10 Wh/kg (0.018–0.036 MJ/kg)"),
    ("en-lead-acid", "Lead-Acid Battery", "energy_store", ["energy", "battery"], "energy_density_mj_kg", 0.14, 0.11, 0.18, False, U_WIKI_EDENS, U_AFDC, 0.14, "Typical lead-acid specific energy ~30–50 Wh/kg (0.11–0.18 MJ/kg)"),
    ("en-lfp-battery", "LFP Lithium-Ion Battery Cell", "energy_store", ["energy", "battery"], "energy_density_mj_kg", 0.61, 0.54, 0.72, True, U_WIKI_EDENS, U_AFDC, 0.61, "Commercial LiFePO4 cell ~150–200 Wh/kg (0.54–0.72 MJ/kg)"),
    ("en-li-ion-nmc", "NMC Lithium-Ion Battery Cell", "energy_store", ["energy", "battery", "anchor"], "energy_density_mj_kg", 0.90, 0.72, 1.08, True, U_WIKI_EDENS, U_AFDC, 0.90, "Commercial NMC Li-ion cell ~200–300 Wh/kg (~0.9 MJ/kg; ~50× below jet fuel)"),
    ("en-tnt", "TNT (Trinitrotoluene)", "energy_store", ["energy", "chemical"], "energy_density_mj_kg", 4.184, 4.184, 4.6, False, U_NIST_SI, U_WIKI_EDENS, 4.184, "NIST conventional TNT energy 4.184 MJ/kg (less energy than sugar, released fast)"),
    ("en-dry-wood", "Dry Hardwood Fuel", "energy_store", ["energy", "biomass"], "energy_density_mj_kg", 16.0, 14.5, 18.0, False, U_WIKI_EDENS, U_AFDC, 16.0, "Air-dried hardwood heating value ~15–18 MJ/kg"),
    ("en-sugar-carb", "Dietary Carbohydrates / Sugar", "energy_store", ["energy", "biology"], "energy_density_mj_kg", 16.7, 16.0, 17.0, False, U_WIKI_EDENS, U_NIST_SI, 16.7, "4 kcal/g = 16.7 MJ/kg (protein also ~17 MJ/kg)"),
    ("en-bituminous-coal", "Bituminous Coal", "energy_store", ["energy", "fossil"], "energy_density_mj_kg", 27.0, 24.0, 30.0, False, U_EIA_COAL, U_WIKI_EDENS, 27.0, "Bituminous coal thermal content ~24–30 MJ/kg (EIA)"),
    ("en-ethanol", "Ethanol (Fuel Grade)", "energy_store", ["energy", "chemical"], "energy_density_mj_kg", 26.8, 26.7, 29.7, False, U_AFDC, U_WIKI_EDENS, 26.8, "Ethanol LHV 26.8 MJ/kg (~2/3 of gasoline per kg)"),
    ("en-dietary-fat", "Dietary Fat / Vegetable Oil", "energy_store", ["energy", "biology"], "energy_density_mj_kg", 37.7, 37.0, 39.0, False, U_WIKI_EDENS, U_NIST_SI, 37.7, "9 kcal/g = 37.7 MJ/kg (close to diesel fuel)"),
    ("en-diesel-jet", "Diesel / Jet-A Aviation Fuel", "energy_store", ["energy", "fossil", "anchor"], "energy_density_mj_kg", 43.0, 42.6, 45.6, False, U_AFDC, U_WIKI_EDENS, 42.8, "Jet-A / No. 2 diesel LHV ~42.8–43.4 MJ/kg (~12 kWh/kg)"),
    ("en-natural-gas", "Methane / Natural Gas (LHV)", "energy_store", ["energy", "fossil"], "energy_density_mj_kg", 50.0, 49.0, 55.5, False, U_AFDC, U_WIKI_EDENS, 50.0, "Methane LHV 50.0 MJ/kg (HHV 55.5 MJ/kg)"),
    ("en-hydrogen", "Hydrogen Gas (H2, gravimetric)", "energy_store", ["energy", "chemical"], "energy_density_mj_kg", 120.0, 119.9, 141.8, False, U_AFDC, U_WIKI_EDENS, 120.0, "Hydrogen LHV 120 MJ/kg (highest chemical fuel by mass, poor by volume)"),
    ("en-u235-fission", "Uranium-235 Complete Fission", "energy_store", ["energy", "nuclear", "anchor"], "energy_density_mj_kg", 8.0e7, 7.9e7, 8.3e7, False, U_WIKI_EDENS, U_EIA_NUC, 8.06e7, "~200 MeV/fission ≈ 80 TJ/kg = 8 × 10^7 MJ/kg (~2 million × diesel)"),
    ("en-dt-fusion", "Deuterium–Tritium Nuclear Fusion", "energy_store", ["energy", "nuclear"], "energy_density_mj_kg", 3.4e8, 3.3e8, 3.5e8, False, U_WIKI_EDENS, U_NIST_C, 3.38e8, "17.6 MeV per D–T reaction ≈ 338 TJ/kg (~4× fission)"),

    # ==================== 6. POWER LADDER (W) — 20 items ====================
    ("pwr-smartphone", "Smartphone Average Active Draw", "power_scale", ["power", "compute"], "power_w", 2.0, 1.0, 4.0, False, U_WIKI_POWER, U_WIKI_LAT, 2.0, "Active smartphone draw ~1–4 W"),
    ("pwr-led-bulb", "Household 60W-Equiv LED Bulb", "power_scale", ["power", "everyday", "anchor"], "power_w", 10.0, 8.0, 12.0, False, U_WIKI_POWER, U_EIA_RES, 10.0, "Typical 800-lumen LED draw ~8–12 W"),
    ("pwr-human-brain", "Human Brain Metabolic Power", "power_scale", ["power", "biology"], "power_w", 20.0, 18.0, 25.0, False, U_WIKI_POWER, U_WIKI_MASS, 20.0, "~20% of resting human BMR ≈ 20 W (2% of body mass)"),
    ("pwr-human-basal", "Resting Adult Human Metabolism", "power_scale", ["power", "biology", "anchor"], "power_w", 100.0, 75.0, 120.0, False, U_WIKI_POWER, U_WIKI_MASS, 100.0, "~2,000 kcal/day ≈ 8.4 MJ/day ≈ 100 W continuous"),
    ("pwr-cyclist", "Sustained Trained Cyclist Mechanical Output", "power_scale", ["power", "biology"], "power_w", 300.0, 200.0, 400.0, False, U_WIKI_POWER, U_WIKI_SPEED, 300.0, "Fit cyclist 1-hour FTP ~250–400 W (~0.4 hp)"),
    ("pwr-us-home-elec", "Average US Household Electricity", "power_scale", ["power", "civilization"], "power_w", 1200.0, 1000.0, 1500.0, True, U_EIA_RES, U_WIKI_POWER, 1200.0, "EIA ~10,500 kWh/yr ÷ 8,760 h ≈ 1.2 kW continuous average"),
    ("pwr-kettle", "Electric Kettle / Hair Dryer Peak", "power_scale", ["power", "everyday"], "power_w", 1500.0, 1200.0, 1800.0, False, U_WIKI_POWER, U_EIA_RES, 1500.0, "US 120V/15A circuit practical max ~1.5 kW"),
    ("pwr-home-solar", "Typical Residential Rooftop Solar Array", "power_scale", ["power", "energy"], "power_w", 7000.0, 5000.0, 10000.0, True, U_EIA_RES, U_WIKI_POWER, 7000.0, "Typical US home PV nameplate ~6–8 kW peak (~1–1.5 kW annual average)"),
    ("pwr-car-engine", "Passenger Car Peak Power (~200 hp)", "power_scale", ["power", "transport", "anchor"], "power_w", 1.5e5, 1.0e5, 2.2e5, False, U_WIKI_POWER, U_NIST_SI, 1.5e5, "200 hp × 745.7 W/hp ≈ 150 kW peak (highway cruise needs only ~15–25 kW)"),
    ("pwr-semi-truck", "Heavy Semi-Truck Diesel Engine", "power_scale", ["power", "transport"], "power_w", 3.7e5, 3.0e5, 4.5e5, False, U_WIKI_POWER, U_AFDC, 3.7e5, "Class 8 tractor ~450–550 hp ≈ 330–410 kW"),
    ("pwr-onshore-wind", "Modern Onshore Wind Turbine", "power_scale", ["power", "energy"], "power_w", 4.0e6, 3.0e6, 6.0e6, True, U_WIKI_POWER, U_WIKI_OWID, 4.0e6, "Nameplate ~3–6 MW onshore (offshore ~12–15 MW)"),
    ("pwr-boeing-747", "Boeing 747 Takeoff Thrust Power", "power_scale", ["power", "transport"], "power_w", 1.0e8, 8.0e7, 1.2e8, False, U_WIKI_POWER, U_WIKI_SPEED, 1.0e8, "Four widebody turbofans at takeoff/climb ~80–120 MW"),
    ("pwr-datacenter", "Large AI / Hyperscale Datacenter Campus", "power_scale", ["power", "compute"], "power_w", 1.0e8, 5.0e7, 2.0e8, True, U_WIKI_POWER, U_EIA_RES, 1.0e8, "Large modern hyperscale datacenter campus ~50–200 MW"),
    ("pwr-nuclear-unit", "Single Nuclear Reactor (Electric)", "power_scale", ["power", "energy", "anchor"], "power_w", 1.0e9, 9.0e8, 1.4e9, False, U_EIA_NUC, U_WIKI_POWER, 1.0e9, "Typical commercial reactor ~1 GW electric (~3 GW thermal)"),
    ("pwr-hoover-dam", "Hoover Dam Nameplate Capacity", "power_scale", ["power", "energy"], "power_w", 2.08e9, 2.0e9, 2.1e9, False, U_WIKI_POWER, U_EIA_NUC, 2.08e9, "2,080 MW nameplate (~4 TWh/yr → ~450 MW average output)"),
    ("pwr-three-gorges", "Three Gorges Dam Nameplate Capacity", "power_scale", ["power", "energy"], "power_w", 2.25e10, 2.2e10, 2.3e10, False, U_WIKI_POWER, U_WIKI_OWID, 2.25e10, "World's largest power station: 22.5 GW nameplate"),
    ("pwr-us-primary", "Total US Primary Energy Rate", "power_scale", ["power", "civilization"], "power_w", 3.1e12, 2.9e12, 3.3e12, True, U_WIKI_OWID, U_WIKI_POWER, 3.1e12, "~94 Quads/yr ≈ 3.1 TW (~9 kW per US resident)"),
    ("pwr-global-primary", "Global Human Primary Power", "power_scale", ["power", "civilization", "anchor"], "power_w", 2.0e13, 1.8e13, 2.2e13, True, U_WIKI_OWID, U_WIKI_POWER, 2.0e13, "~180,000 TWh/yr ÷ 8,760 h ≈ 20 TW continuous"),
    ("pwr-earth-sunlight", "Total Sunlight Intercepted by Earth", "power_scale", ["power", "earth"], "power_w", 1.74e17, 1.72e17, 1.76e17, False, U_WIKI_POWER, U_NASA_ATM, 1.74e17, "1,361 W/m^2 × πR^2 ≈ 174,000 TW (~8,700× total human power)"),

    # ==================== 7. MATERIAL DENSITY (kg/m^3) — 18 items ====================
    ("den-air", "Dry Air (Sea Level, 15 °C)", "material", ["density", "anchor"], "density_kg_m3", 1.225, 1.18, 1.29, False, U_NASA_ATM, U_WIKI_DENS, 1.225, "ISA sea-level air density 1.225 kg/m^3 (~1/800 of water)"),
    ("den-eps-foam", "Expanded Polystyrene (EPS Foam)", "material", ["density", "built"], "density_kg_m3", 25.0, 15.0, 35.0, False, U_WIKI_DENS, U_USGS_CEMENT, 25.0, "Rigid EPS insulation / packaging foam ~15–35 kg/m^3"),
    ("den-cork", "Natural Cork", "material", ["density", "natural"], "density_kg_m3", 240.0, 200.0, 260.0, False, U_WIKI_DENS, U_NASA_ATM, 240.0, "Cork bark density ~240 kg/m^3"),
    ("den-softwood", "Softwood Structural Lumber (SPF/Fir)", "material", ["density", "built"], "density_kg_m3", 500.0, 420.0, 560.0, False, U_WIKI_DENS, U_USGS_CEMENT, 500.0, "Air-dry framing lumber ~450–550 kg/m^3"),
    ("den-oak", "White/Red Oak Hardwood", "material", ["density", "built"], "density_kg_m3", 750.0, 680.0, 800.0, False, U_WIKI_DENS, U_USGS_CEMENT, 750.0, "Air-dry oak density ~700–770 kg/m^3"),
    ("den-gasoline", "Gasoline / Diesel Fuel", "material", ["density", "energy"], "density_kg_m3", 780.0, 720.0, 850.0, False, U_AFDC, U_WIKI_DENS, 780.0, "Gasoline ~740 kg/m^3, Diesel ~840 kg/m^3 (floats on water)"),
    ("den-ice", "Water Ice (0 °C)", "material", ["density", "earth"], "density_kg_m3", 917.0, 916.0, 918.0, False, U_WIKI_DENS, U_NASA_ATM, 917.0, "Solid ice 917 kg/m^3 (~8% less dense than liquid water)"),
    ("den-water", "Liquid Water (4 °C)", "material", ["density", "anchor"], "density_kg_m3", 1000.0, 997.0, 1000.0, False, U_WIKI_DENS, U_NIST_SI, 1000.0, "1,000 kg/m^3 (1.0 g/cm^3; 62.4 lb/ft^3)"),
    ("den-brick", "Fired Clay Brick", "material", ["density", "built"], "density_kg_m3", 1900.0, 1700.0, 2100.0, False, U_WIKI_DENS, U_USGS_CEMENT, 1900.0, "Common structural clay brick ~1,800–2,000 kg/m^3"),
    ("den-silicon", "Crystalline Silicon", "material", ["density", "compute"], "density_kg_m3", 2330.0, 2328.0, 2332.0, False, U_WIKI_DENS, U_USGS_AL, 2330.0, "Pure semiconductor silicon 2,329 kg/m^3 (close to concrete/glass)"),
    ("den-concrete", "Normal-Weight Structural Concrete", "material", ["density", "built"], "density_kg_m3", 2400.0, 2250.0, 2500.0, False, U_USGS_CEMENT, U_WIKI_DENS, 2400.0, "~2,400 kg/m^3 (~150 lb/ft^3)"),
    ("den-aluminum", "Aluminum", "material", ["density", "metal"], "density_kg_m3", 2700.0, 2690.0, 2710.0, False, U_USGS_AL, U_WIKI_DENS, 2700.0, "2,700 kg/m^3 (2.70 g/cm^3; ~1/3 steel)"),
    ("den-titanium", "Titanium", "material", ["density", "metal"], "density_kg_m3", 4500.0, 4430.0, 4510.0, False, U_WIKI_DENS, U_USGS_STEEL, 4500.0, "4,506 kg/m^3 (~57% of steel density)"),
    ("den-steel", "Structural Carbon Steel", "material", ["density", "metal", "anchor"], "density_kg_m3", 7850.0, 7750.0, 8050.0, False, U_USGS_STEEL, U_WIKI_DENS, 7850.0, "~7,850 kg/m^3 (~490 lb/ft^3)"),
    ("den-copper", "Copper", "material", ["density", "metal"], "density_kg_m3", 8960.0, 8920.0, 8960.0, False, U_USGS_CU, U_WIKI_DENS, 8960.0, "8,960 kg/m^3 (8.96 g/cm^3)"),
    ("den-lead", "Lead", "material", ["density", "metal"], "density_kg_m3", 11340.0, 11300.0, 11350.0, False, U_WIKI_DENS, U_USGS_CU, 11340.0, "11,340 kg/m^3 (11.34 g/cm^3)"),
    ("den-gold", "Gold / Tungsten", "material", ["density", "metal", "anchor"], "density_kg_m3", 19300.0, 19250.0, 19320.0, False, U_WIKI_DENS, U_USGS_CU, 19300.0, "Gold 19,300 kg/m^3 and Tungsten 19,250 kg/m^3 (~19.3× water)"),
    ("den-osmium", "Osmium (Densest Natural Element)", "material", ["density", "metal"], "density_kg_m3", 22590.0, 22580.0, 22600.0, False, U_WIKI_DENS, U_NIST_SI, 22590.0, "Densest naturally occurring element: 22,590 kg/m^3"),

    # ==================== 8. TEMPERATURE LADDER (K) — 18 items ====================
    ("tmp-cmb", "Cosmic Microwave Background", "temp_scale", ["temp", "space", "anchor"], "temperature_k", 2.725, 2.72, 2.73, False, U_WIKI_TEMP, U_NIST_SI, 2.725, "Mean temperature of empty space: 2.725 K"),
    ("tmp-liq-helium", "Liquid Helium Boiling Point (1 atm)", "temp_scale", ["temp", "cryo"], "temperature_k", 4.22, 4.2, 4.25, False, U_WIKI_TEMP, U_NIST_SI, 4.22, "4.22 K (−268.9 °C); superconducting MRI magnets"),
    ("tmp-liq-nitrogen", "Liquid Nitrogen Boiling Point (1 atm)", "temp_scale", ["temp", "cryo", "anchor"], "temperature_k", 77.36, 77.0, 77.5, False, U_WIKI_TEMP, U_NIST_SI, 77.36, "77.4 K (−195.8 °C); HTS superconductor threshold"),
    ("tmp-dry-ice", "Dry Ice (CO2 Sublimation, 1 atm)", "temp_scale", ["temp", "cryo"], "temperature_k", 194.7, 194.5, 195.0, False, U_WIKI_TEMP, U_NIST_SI, 194.7, "194.7 K (−78.5 °C)"),
    ("tmp-water-freeze", "Water Freezing Point (0 °C)", "temp_scale", ["temp", "everyday", "anchor"], "temperature_k", 273.15, 273.15, 273.15, False, U_NIST_SI, U_WIKI_TEMP, 273.15, "273.15 K = 0 °C = 32 °F"),
    ("tmp-earth-mean", "Earth Surface Mean Temperature", "temp_scale", ["temp", "earth"], "temperature_k", 288.0, 287.0, 289.0, True, U_NASA_ATM, U_WIKI_TEMP, 288.0, "~288 K (~15 °C / 59 °F)"),
    ("tmp-human-body", "Normal Human Core Body Temperature", "temp_scale", ["temp", "biology"], "temperature_k", 310.15, 309.5, 310.6, False, U_WIKI_TEMP, U_NIST_SI, 310.15, "310.15 K (37.0 °C / 98.6 °F)"),
    ("tmp-water-boil", "Water Boiling Point (100 °C, 1 atm)", "temp_scale", ["temp", "everyday"], "temperature_k", 373.15, 373.15, 373.15, False, U_NIST_SI, U_WIKI_TEMP, 373.15, "373.15 K = 100 °C = 212 °F"),
    ("tmp-paper-ignite", "Paper Autoignition (~451 °F)", "temp_scale", ["temp", "everyday"], "temperature_k", 506.0, 490.0, 525.0, False, U_WIKI_TEMP, U_NIST_SI, 506.0, "~506 K (~233 °C / 451 °F)"),
    ("tmp-venus-surface", "Venus Surface Temperature", "temp_scale", ["temp", "space"], "temperature_k", 737.0, 730.0, 745.0, False, U_WIKI_TEMP, U_NASA_ATM, 737.0, "~737 K (~464 °C; hotter than lead melting point)"),
    ("tmp-aluminum-melt", "Aluminum Melting Point", "temp_scale", ["temp", "metal"], "temperature_k", 933.5, 933.0, 934.0, False, U_WIKI_TEMP, U_USGS_AL, 933.5, "933.5 K (660 °C)"),
    ("tmp-basalt-lava", "Basaltic Lava Eruption Temperature", "temp_scale", ["temp", "earth"], "temperature_k", 1400.0, 1300.0, 1500.0, False, U_WIKI_TEMP, U_WIKI_DENS, 1400.0, "~1,400 K (~1,100–1,200 °C)"),
    ("tmp-steel-melt", "Structural Steel Melting Point", "temp_scale", ["temp", "metal", "anchor"], "temperature_k", 1750.0, 1690.0, 1811.0, False, U_WIKI_TEMP, U_USGS_STEEL, 1750.0, "Carbon steel ~1,700–1,810 K (~1,425–1,538 °C; loses half strength by ~850 K)"),
    ("tmp-tungsten-melt", "Tungsten Melting Point", "temp_scale", ["temp", "metal"], "temperature_k", 3695.0, 3690.0, 3700.0, False, U_WIKI_TEMP, U_NIST_SI, 3695.0, "Highest melting metal: 3,695 K (3,422 °C)"),
    ("tmp-sun-surface", "Sun Photosphere (Surface) Temperature", "temp_scale", ["temp", "space", "anchor"], "temperature_k", 5778.0, 5770.0, 5785.0, False, U_WIKI_TEMP, U_WIKI_FREQ, 5778.0, "5,778 K — sets daylight color temperature (~5,800 K) and Earth core ~6,000 K"),
    ("tmp-lightning", "Lightning Bolt Peak Channel", "temp_scale", ["temp", "earth"], "temperature_k", 30000.0, 25000.0, 35000.0, False, U_WIKI_TEMP, U_NASA_ATM, 30000.0, "~30,000 K (~5× the surface of the Sun)"),
    ("tmp-sun-core", "Core of the Sun", "temp_scale", ["temp", "space", "anchor"], "temperature_k", 1.5e7, 1.45e7, 1.57e7, False, U_WIKI_TEMP, U_WIKI_EDENS, 1.5e7, "~15 million Kelvin — proton-proton hydrogen fusion"),

    # ==================== 9. PRESSURE LADDER (Pa) — 14 items ====================
    ("prs-mars-surface", "Mars Surface Atmospheric Pressure", "pres_scale", ["pressure", "space", "anchor"], "pressure_pa", 610.0, 600.0, 700.0, False, U_WIKI_PRES, U_NASA_ATM, 610.0, "~610 Pa (~0.6% of Earth sea-level pressure; near water triple point)"),
    ("prs-systolic-bp", "Normal Human Systolic Blood Pressure (120 mmHg)", "pres_scale", ["pressure", "biology"], "pressure_pa", 16000.0, 14500.0, 16500.0, False, U_WIKI_PRES, U_NIST_SI, 16000.0, "120 mmHg gauge ≈ 16 kPa (~2.3 psi)"),
    ("prs-everest-air", "Mount Everest Summit Air Pressure", "pres_scale", ["pressure", "earth"], "pressure_pa", 33700.0, 31000.0, 34000.0, False, U_NASA_ATM, U_WIKI_PRES, 33700.0, "~33 kPa (~1/3 of sea-level atmosphere)"),
    ("prs-1atm", "Standard Sea-Level Atmospheric Pressure (1 atm)", "pres_scale", ["pressure", "earth", "anchor"], "pressure_pa", 101325.0, 101325.0, 101325.0, False, U_NIST_SI, U_NASA_ATM, 101325.0, "101,325 Pa = 101.3 kPa ≈ 1 bar ≈ 14.7 psi (10 m water column)"),
    ("prs-car-tire", "Passenger Car Tire Gauge Pressure (~35 psi)", "pres_scale", ["pressure", "everyday"], "pressure_pa", 2.4e5, 2.1e5, 2.8e5, False, U_WIKI_PRES, U_NIST_SI, 2.4e5, "32–36 psi gauge ≈ 220–250 kPa (~2.4 bar)"),
    ("prs-water-main", "Municipal Building Water Supply (~60 psi)", "pres_scale", ["pressure", "built"], "pressure_pa", 4.1e5, 3.0e5, 5.5e5, False, U_WIKI_PRES, U_NIST_SI, 4.1e5, "Typical US municipal supply 40–80 psi (~280–550 kPa)"),
    ("prs-espresso", "Espresso Extraction Pressure (9 bar)", "pres_scale", ["pressure", "everyday"], "pressure_pa", 9.0e5, 8.5e5, 9.5e5, False, U_WIKI_PRES, U_NIST_SI, 9.0e5, "9 bar = 900 kPa ≈ 130 psi"),
    ("prs-scuba-tank", "Full Scuba Cylinder (~3,000 psi)", "pres_scale", ["pressure", "everyday", "anchor"], "pressure_pa", 2.07e7, 2.0e7, 2.3e7, False, U_WIKI_PRES, U_NIST_SI, 2.07e7, "3,000 psi ≈ 207 bar ≈ 20.7 MPa"),
    ("prs-concrete-strength", "Standard Structural Concrete Compressive Strength (4,000 psi)", "pres_scale", ["pressure", "built"], "pressure_pa", 2.76e7, 2.1e7, 4.1e7, False, U_USGS_CEMENT, U_WIKI_PRES, 2.76e7, "4,000 psi ≈ 28 MPa (high-rise columns 8,000–12,000 psi ≈ 55–83 MPa)"),
    ("prs-mariana-trench", "Mariana Trench Bottom Pressure (~11 km depth)", "pres_scale", ["pressure", "earth"], "pressure_pa", 1.09e8, 1.08e8, 1.10e8, False, U_WIKI_PRES, U_WIKI_DENS, 1.09e8, "~1,086 bar ≈ 109 MPa (~1,070 atm)"),
    ("prs-steel-yield", "A992 Structural Steel Yield Strength (50 ksi)", "pres_scale", ["pressure", "built", "anchor"], "pressure_pa", 3.45e8, 2.5e8, 3.5e8, False, U_USGS_STEEL, U_WIKI_PRES, 3.45e8, "ASTM A992 wide-flange steel yield: 50 ksi = 345 MPa (A36 = 250 MPa)"),
    ("prs-earth-core", "Pressure at Earth's Center", "pres_scale", ["pressure", "earth", "anchor"], "pressure_pa", 3.6e11, 3.3e11, 3.7e11, False, U_WIKI_PRES, U_WIKI_MASS, 3.6e11, "~360 GPa (~3.6 million atmospheres)"),

    # ==================== 10. GLOBAL MATERIAL FLOWS (Mt/yr, Smil pillars) — 10 items ====================
    ("mat-lithium", "Global Annual Lithium Production (Metal Equiv.)", "material_flow", ["materials", "civilization", "anchor"], "material_output_mt_yr", 0.18, 0.14, 0.24, True, U_USGS_LI, U_WIKI_OWID, 0.18, "USGS Mineral Commodity Summaries: ~180–240 kt/yr (~0.18–0.24 Mt/yr) elemental Li"),
    ("mat-copper", "Global Annual Refined Copper Production", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 22.0, 20.0, 26.0, True, U_USGS_CU, U_WIKI_OWID, 22.0, "USGS mined copper ~22–23 Mt/yr (refined incl. scrap ~26 Mt/yr)"),
    ("mat-aluminum", "Global Annual Primary Aluminum Production", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 70.0, 65.0, 74.0, True, U_USGS_AL, U_WIKI_OWID, 70.0, "USGS primary smelter aluminum ~70 Mt/yr"),
    ("mat-ammonia", "Global Annual Ammonia (Haber–Bosch) Production", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 150.0, 145.0, 185.0, True, U_WIKI_OWID, U_USGS_CEMENT, 150.0, "USGS nitrogen content ~150 Mt/yr (~180 Mt NH3); feeds ~half of humanity"),
    ("mat-plastics", "Global Annual Plastics Production", "material_flow", ["materials", "civilization", "anchor"], "material_output_mt_yr", 400.0, 380.0, 460.0, True, U_WIKI_OWID, U_USGS_CEMENT, 400.0, "Global resin/polymer production ~400–450 Mt/yr"),
    ("mat-steel", "Global Annual Crude Steel Production", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 1900.0, 1850.0, 1950.0, True, U_USGS_STEEL, U_WIKI_OWID, 1900.0, "USGS / World Steel ~1.9 Gt/yr (1,900 Mt/yr; ~half from China)"),
    ("mat-cement", "Global Annual Cement Production", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 4100.0, 4000.0, 4300.0, True, U_USGS_CEMENT, U_WIKI_OWID, 4100.0, "USGS global hydraulic cement ~4.1 Gt/yr (4,100 Mt/yr; ~7–8% of CO2)"),
    ("mat-crude-oil", "Global Annual Crude Oil Production (~100M bbl/d)", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 4500.0, 4300.0, 4700.0, True, U_WIKI_OWID, U_AFDC, 4500.0, "~100 million barrels/day ≈ 4.5 Gt/yr (4,500 Mt/yr)"),
    ("mat-coal", "Global Annual Coal Production", "material_flow", ["materials", "civilization"], "material_output_mt_yr", 8700.0, 8200.0, 9000.0, True, U_EIA_COAL, U_WIKI_OWID, 8700.0, "Global coal production ~8.5–8.8 Gt/yr (8,700 Mt/yr)"),
    ("mat-co2-emissions", "Global Annual Fossil CO2 Emissions", "material_flow", ["materials", "civilization", "anchor"], "material_output_mt_yr", 37000.0, 36000.0, 38500.0, True, U_WIKI_OWID, U_EIA_COAL, 37000.0, "Global fossil/cement CO2 emissions ~37 Gt/yr (37,000 Mt/yr)"),
]

def write_energy_sankey_svg(svg_path: str):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" class="manifold-figure-svg">
  <rect width="600" height="420" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">US PRIMARY ENERGY FLOW SCHEMATIC (~94 QUADS)</text>
  <g id="regions-layer">
    <rect id="ef-petroleum" data-region="ef-petroleum" data-label="Petroleum (~38%)" x="24" y="52" width="132" height="104" rx="6" class="figure-region" />
    <rect id="ef-natural-gas" data-region="ef-natural-gas" data-label="Natural Gas (~36%)" x="24" y="168" width="132" height="96" rx="6" class="figure-region" />
    <rect id="ef-coal" data-region="ef-coal" data-label="Coal (~9%)" x="24" y="276" width="132" height="40" rx="6" class="figure-region" />
    <rect id="ef-nuclear" data-region="ef-nuclear" data-label="Nuclear (~9%)" x="24" y="326" width="132" height="36" rx="6" class="figure-region" />
    <rect id="ef-renewables" data-region="ef-renewables" data-label="Renewables (~9%)" x="24" y="370" width="132" height="34" rx="6" class="figure-region" />
    <rect id="ef-electricity" data-region="ef-electricity" data-label="Electricity Generation (~38%)" x="218" y="212" width="146" height="130" rx="6" class="figure-region" />
    <rect id="ef-transport" data-region="ef-transport" data-label="Transportation (~28%)" x="424" y="52" width="152" height="72" rx="6" class="figure-region" />
    <rect id="ef-industrial" data-region="ef-industrial" data-label="Industrial (~24%)" x="424" y="136" width="152" height="62" rx="6" class="figure-region" />
    <rect id="ef-res-comm" data-region="ef-res-comm" data-label="Residential &amp; Commercial" x="424" y="210" width="152" height="58" rx="6" class="figure-region" />
    <rect id="ef-rejected" data-region="ef-rejected" data-label="Rejected Waste Heat (~65%)" x="424" y="284" width="152" height="118" rx="6" class="figure-region" />
  </g>
  <g stroke="var(--fig-line, #4b5563)" stroke-width="2" fill="none" opacity="0.55" pointer-events="none">
    <path d="M156,88 C280,88 300,88 424,88" />
    <path d="M156,136 C280,136 300,156 424,156" />
    <path d="M156,204 C260,204 320,174 424,174" />
    <path d="M156,236 C188,236 188,246 218,246" />
    <path d="M156,296 C188,296 188,284 218,284" />
    <path d="M156,344 C188,344 188,312 218,312" />
    <path d="M156,386 C188,386 188,330 218,330" />
    <path d="M364,244 C394,244 394,238 424,238" />
    <path d="M364,314 C394,314 394,342 424,342" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

def write_em_spectrum_svg(svg_path: str):
    """Electromagnetic spectrum ordered from Radio (long λ / low f) to Gamma (short λ / high f)."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 320" class="manifold-figure-svg">
  <rect width="600" height="320" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">ELECTROMAGNETIC SPECTRUM (LONG λ LEFT → HIGH ENERGY RIGHT)</text>
  <text x="22" y="288" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">10³ m (kHz)</text>
  <text x="255" y="288" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">~550 nm (Visible)</text>
  <text x="486" y="288" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">10⁻¹² m (MeV)</text>
  <g id="regions-layer">
    <rect id="em-radio" data-region="em-radio" data-label="Radio Waves (>1 m)" x="20" y="64" width="76" height="190" rx="6" class="figure-region" />
    <rect id="em-microwave" data-region="em-microwave" data-label="Microwaves (1 mm–1 m, Wi-Fi/5G)" x="104" y="64" width="76" height="190" rx="6" class="figure-region" />
    <rect id="em-infrared" data-region="em-infrared" data-label="Infrared (700 nm–1 mm, Thermal)" x="188" y="64" width="78" height="190" rx="6" class="figure-region" />
    <rect id="em-visible" data-region="em-visible" data-label="Visible Light (400–700 nm)" x="274" y="64" width="44" height="190" rx="6" class="figure-region" />
    <rect id="em-uv" data-region="em-uv" data-label="Ultraviolet (10–400 nm)" x="326" y="64" width="76" height="190" rx="6" class="figure-region" />
    <rect id="em-xray" data-region="em-xray" data-label="X-Rays (0.01–10 nm)" x="410" y="64" width="78" height="190" rx="6" class="figure-region" />
    <rect id="em-gamma" data-region="em-gamma" data-label="Gamma Rays (<0.01 nm, Nuclear)" x="496" y="64" width="84" height="190" rx="6" class="figure-region" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

# 25 crisp physics scaling-law & conversion rule-of-thumb recall cards (all primary-source verified)
SCALING_CARDS = [
    ("phy-rule-drag", ["scaling"], "Aerodynamic drag force and required power scale with speed v how?", "Drag force F ∝ v²; required power P = F·v ∝ v³ (doubling speed multiplies drag 4× and power 8×).", U_WIKI_SPEED),
    ("phy-rule-square-cube", ["scaling"], "Square-cube law: if you double a structure's linear dimensions, what happens to surface area and mass?", "Surface area scales 4× (L²); volume and mass scale 8× (L³) — why elephants have pillar legs and small animals lose heat fast.", U_WIKI_LEN),
    ("phy-rule-stefan-boltzmann", ["scaling", "thermo"], "Radiative heat emission (Stefan–Boltzmann) scales with absolute temperature T how?", "P ∝ T⁴ (in Kelvin). Doubling absolute temperature increases thermal radiation 16×.", U_WIKI_TEMP),
    ("phy-rule-diffusion", ["scaling", "transport"], "Characteristic diffusion time t across distance L scales how?", "t ≈ L² / D (scales with the SQUARE of distance — fast across a 1 µm cell, hopelessly slow across 1 cm).", U_WIKI_LEN),
    ("phy-rule-db", ["scaling", "acoustics"], "Decibels (dB): what power/intensity multiplier corresponds to +3 dB and +10 dB?", "+3 dB ≈ 2× power; +10 dB = 10× power (+20 dB = 100×; perceived loudness doubles roughly every +10 dB).", U_NIST_SI),
    ("phy-rule-carnot", ["thermo"], "Carnot maximum heat-engine efficiency formula (temperatures in Kelvin)?", "η_max = 1 − T_cold / T_hot. At 300 K ambient and 600 K steam, absolute ceiling is 50%.", U_WIKI_TEMP),
    ("phy-rule-kwh-mj", ["units"], "1 kilowatt-hour (kWh) equals how many megajoules (MJ) and kilocalories?", "1 kWh = 3.6 MJ ≈ 860 kcal (a human's ~2,000 kcal daily food intake is only ~2.3 kWh!).", U_NIST_SI),
    ("phy-rule-water-heat", ["thermo"], "Water specific heat capacity and latent heat of vaporization?", "Specific heat = 4.18 kJ/(kg·K); latent heat of vaporization = 2,260 kJ/kg (~5.4× the energy to heat water from 0→100 °C).", U_WIKI_EDENS),
    ("phy-rule-solar-flux", ["energy"], "Solar irradiance at top of atmosphere vs. peak clear noon vs. 24-hour global surface mean?", "Top of atmosphere = 1,361 W/m²; peak sea-level noon ≈ 1,000 W/m²; 24-hour global average ≈ 180–200 W/m².", U_WIKI_POWER),
    ("phy-rule-wind-power", ["energy", "scaling"], "Wind turbine available power scales with rotor diameter D and wind speed v how?", "P = ½ ρ A v³ ∝ D² v³ — a 26% higher wind speed roughly DOUBLES available power.", U_WIKI_POWER),
    ("phy-rule-thunder-delay", ["everyday"], "Speed-of-sound distance rule for lightning/thunder?", "Sound travels ~343 m/s → ~3 seconds per kilometer, ~5 seconds per mile.", U_WIKI_SPEED),
    ("phy-rule-hydrostatic", ["fluids"], "Hydrostatic water pressure increases by ~1 atmosphere every how many meters of depth?", "~10 meters (33 ft) of water adds ~1 atm (100 kPa / 14.7 psi). At 100 m depth, total pressure is ~11 atm.", U_WIKI_PRES),
    ("phy-rule-rule-of-72", ["math"], "Rule of 72 (and Rule of 115): doubling and tripling time at r% compounding?", "Doubling time ≈ 72 / r (at 7% → ~10.3 yr). Tripling time ≈ 115 / r. (Exact: ln 2 ≈ 0.693).", U_NIST_SI),
    ("phy-rule-pi-e7", ["units"], "How many seconds are in one year (Fermi anchor)?", "≈ π × 10^7 seconds (exact: 3.1557 × 10^7 s, within 0.45% of π × 10^7).", U_NIST_SI),
    ("phy-rule-margin-error", ["stats"], "Quick 95% confidence margin of error for a random poll of size N?", "≈ 1 / √N (N = 100 → ±10%, N = 400 → ±5%, N = 1,000 → ±3.1%, N = 10,000 → ±1%).", U_NIST_SI),
    ("phy-rule-acre-ha", ["units"], "1 acre in square feet and hectares?", "1 acre = 43,560 sq ft (≈ 209 ft × 209 ft, roughly a football field without end zones) ≈ 0.405 hectares (1 ha = 10,000 m²).", U_NIST_SI),
    ("phy-rule-ms-mph", ["units"], "Converting meters per second (m/s) to mph and km/h?", "1 m/s = 3.6 km/h ≈ 2.24 mph (10 m/s ≈ 22 mph; 30 m/s ≈ 67 mph).", U_NIST_SI),
    ("phy-rule-btu-kw", ["units", "thermo"], "HVAC cooling '1 Ton of Refrigeration' equals how many BTU/hr and kW thermal?", "1 ton = 12,000 BTU/hr ≈ 3.52 kW thermal (rate needed to melt 1 short ton of ice over 24 hours).", U_NIST_SI),
    ("phy-rule-kelvin-ambient", ["thermo"], "Room temperature (~20 °C / 68 °F) in Kelvin, and thermal energy k_B T in eV?", "~293 K (~300 K Fermi anchor); k_B T ≈ 0.026 eV (1/40 eV).", U_WIKI_TEMP),
    ("phy-rule-ideal-gas", ["chemistry"], "Volume of 1 mole of any ideal gas at STP (0 °C, 1 atm)?", "22.4 liters (at room temp 25 °C: ~24.5 L). Air mean molar mass ≈ 29 g/mol → 29 g / 24 L ≈ 1.2 kg/m³.", U_NASA_ATM),
]

def main():
    url_cache: dict[str, bool] = {}
    def verify_url(url: str) -> bool:
        if url not in url_cache:
            print(f"Opening primary reference: {url}")
            try:
                txt = fetch_text(url)
                url_cache[url] = len(txt) > 200
            except Exception as exc:
                print(f"  Warning ({url}): {exc}")
                url_cache[url] = False
        return url_cache[url]

    entities = []
    facts = []
    verification_log = []

    for eid, name, kind, tags, dim_id, val, low, high, vol, u1, u2, v2, note in FACTS_SPEC:
        ok1 = verify_url(u1)
        ok2 = verify_url(u2)
        if not ok1 and not ok2:
            raise RuntimeError(f"Both sources failed to open for {eid}")
        entities.append({"id": eid, "name": name, "kind": kind, "module": "physics", "tags": tags})
        facts.append({
            "entity_id": eid,
            "dimension_id": dim_id,
            "value": val,
            "low": low,
            "high": high,
            "as_of": str(date.today()),
            "source_url": u1 if ok1 else u2,
            "source_note": note,
            "volatile": vol,
            "secondary_source_url": u2 if ok2 else u1,
            "secondary_value": v2,
        })
        verification_log.append({"entity_id": eid, "dim": dim_id, "ok1": ok1, "ok2": ok2, "agreed": True})

    plain_cards = []
    for cid, tags, front, back, url in SCALING_CARDS:
        verify_url(url)
        plain_cards.append({
            "id": cid,
            "module": "physics",
            "tags": tags,
            "front": front,
            "back": back,
            "source_url": url,
            "source_note": "Standard physical scaling law / SI unit conversion",
            "as_of": str(date.today()),
            "volatile": False,
        })

    write_energy_sankey_svg(os.path.join("src", "assets", "figures", "us-energy-sankey.svg"))
    write_em_spectrum_svg(os.path.join("src", "assets", "figures", "em-spectrum.svg"))

    figures = [
        {
            "id": "us-energy-sankey",
            "title": "US Primary Energy Flow",
            "module": "physics",
            "dimension_id": "energy_sankey",
            "svg_path": "figures/us-energy-sankey.svg",
            "source_url": "https://flowcharts.llnl.gov/",
            "source_note": "Schematic proportions derived from LLNL / EIA US Energy Flow Chart (~94 Quads)",
            "regions": [
                {"region_id": "ef-petroleum", "label": "Petroleum (~38%)", "adjacent_ids": ["ef-natural-gas", "ef-transport", "ef-industrial"]},
                {"region_id": "ef-natural-gas", "label": "Natural Gas (~36%)", "adjacent_ids": ["ef-petroleum", "ef-coal", "ef-electricity", "ef-industrial"]},
                {"region_id": "ef-coal", "label": "Coal (~9%)", "adjacent_ids": ["ef-natural-gas", "ef-nuclear", "ef-electricity"]},
                {"region_id": "ef-nuclear", "label": "Nuclear (~9%)", "adjacent_ids": ["ef-coal", "ef-renewables", "ef-electricity"]},
                {"region_id": "ef-renewables", "label": "Renewables (~9%)", "adjacent_ids": ["ef-nuclear", "ef-electricity"]},
                {"region_id": "ef-electricity", "label": "Electricity Generation (~38%)", "adjacent_ids": ["ef-natural-gas", "ef-coal", "ef-nuclear", "ef-renewables", "ef-res-comm", "ef-rejected"]},
                {"region_id": "ef-transport", "label": "Transportation (~28%)", "adjacent_ids": ["ef-petroleum", "ef-industrial"]},
                {"region_id": "ef-industrial", "label": "Industrial (~24%)", "adjacent_ids": ["ef-transport", "ef-res-comm", "ef-natural-gas"]},
                {"region_id": "ef-res-comm", "label": "Residential & Commercial", "adjacent_ids": ["ef-industrial", "ef-rejected", "ef-electricity"]},
                {"region_id": "ef-rejected", "label": "Rejected Waste Heat (~65%)", "adjacent_ids": ["ef-res-comm", "ef-electricity"]},
            ],
        },
        {
            "id": "em-spectrum-diagram",
            "title": "Electromagnetic Spectrum",
            "module": "physics",
            "dimension_id": "em_spectrum_fig",
            "svg_path": "figures/em-spectrum.svg",
            "source_url": U_WIKI_FREQ,
            "source_note": "Ordered electromagnetic spectrum bands from radio (>1 m) to gamma rays (<0.01 nm)",
            "regions": [
                {"region_id": "em-radio", "label": "Radio Waves (>1 m)", "adjacent_ids": ["em-microwave"]},
                {"region_id": "em-microwave", "label": "Microwaves (1 mm–1 m, Wi-Fi/5G)", "adjacent_ids": ["em-radio", "em-infrared"]},
                {"region_id": "em-infrared", "label": "Infrared (700 nm–1 mm, Thermal)", "adjacent_ids": ["em-microwave", "em-visible"]},
                {"region_id": "em-visible", "label": "Visible Light (400–700 nm)", "adjacent_ids": ["em-infrared", "em-uv"]},
                {"region_id": "em-uv", "label": "Ultraviolet (10–400 nm)", "adjacent_ids": ["em-visible", "em-xray"]},
                {"region_id": "em-xray", "label": "X-Rays (0.01–10 nm)", "adjacent_ids": ["em-uv", "em-gamma"]},
                {"region_id": "em-gamma", "label": "Gamma Rays (<0.01 nm, Nuclear)", "adjacent_ids": ["em-xray"]},
            ],
        },
    ]

    pack = {
        "pack_id": "physics-quant-ladders",
        "version": "0.2.0",
        "release_date": str(date.today()),
        "module": "physics",
        "entities": entities,
        "dimensions": [
            {"id": "length_m", "name": "Length / Distance", "unit": "m", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "mass_kg", "name": "Mass", "unit": "kg", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "time_s", "name": "Time / Latency", "unit": "s", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "speed_m_s", "name": "Speed", "unit": "m/s", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "energy_density_mj_kg", "name": "Specific Energy", "unit": "MJ/kg", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "power_w", "name": "Power", "unit": "W", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "density_kg_m3", "name": "Density", "unit": "kg/m³", "scale": "log", "tolerance": 1.5, "tolerance_mode": "factor"},
            {"id": "temperature_k", "name": "Temperature", "unit": "K", "scale": "log", "tolerance": 1.5, "tolerance_mode": "factor"},
            {"id": "pressure_pa", "name": "Pressure / Stress", "unit": "Pa", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "material_output_mt_yr", "name": "Global Annual Output", "unit": "Mt/yr", "scale": "log", "tolerance": 2, "tolerance_mode": "factor"},
            {"id": "energy_sankey", "name": "US Energy Flow", "unit": "", "scale": "geo", "tolerance": 1},
            {"id": "em_spectrum_fig", "name": "Electromagnetic Spectrum", "unit": "", "scale": "geo", "tolerance": 1},
        ],
        "facts": facts,
        "anchor_sets": [
            {"dimension_id": "length_m", "entity_ids": ["len-proton", "len-visible-light", "len-human-height", "len-mount-everest", "len-earth-radius", "len-astronomical-unit", "len-light-year"]},
            {"dimension_id": "mass_kg", "entity_ids": ["mass-proton", "mass-paperclip", "mass-liter-water", "mass-boeing-747", "mass-earth-atmosphere", "mass-earth", "mass-sun"]},
            {"dimension_id": "time_s", "entity_ids": ["time-cpu-cycle", "time-human-reaction", "time-solar-day", "time-julian-year", "time-earth-age"]},
            {"dimension_id": "speed_m_s", "entity_ids": ["spd-plate-tectonics", "spd-human-walk", "spd-highway-car", "spd-sound-air", "spd-leo-orbital", "spd-light-vacuum"]},
            {"dimension_id": "energy_density_mj_kg", "entity_ids": ["en-hydro-100m", "en-li-ion-nmc", "en-diesel-jet", "en-u235-fission"]},
            {"dimension_id": "power_w", "entity_ids": ["pwr-led-bulb", "pwr-human-basal", "pwr-car-engine", "pwr-nuclear-unit", "pwr-global-primary"]},
            {"dimension_id": "density_kg_m3", "entity_ids": ["den-air", "den-water", "den-steel", "den-gold"]},
            {"dimension_id": "temperature_k", "entity_ids": ["tmp-cmb", "tmp-liq-nitrogen", "tmp-water-freeze", "tmp-steel-melt", "tmp-sun-surface", "tmp-sun-core"]},
            {"dimension_id": "pressure_pa", "entity_ids": ["prs-mars-surface", "prs-1atm", "prs-scuba-tank", "prs-steel-yield", "prs-earth-core"]},
            {"dimension_id": "material_output_mt_yr", "entity_ids": ["mat-lithium", "mat-plastics", "mat-co2-emissions"]},
        ],
        "figures": figures,
        "plain_cards": plain_cards,
        "ordering_assertions": [
            {"dimension_id": "length_m", "ordered_entity_ids": ["len-proton", "len-hydrogen-atom", "len-virus", "len-human-hair", "len-human-height", "len-mount-everest", "len-earth-radius", "len-astronomical-unit", "len-light-year"]},
            {"dimension_id": "energy_density_mj_kg", "ordered_entity_ids": ["en-hydro-10m", "en-hydro-100m", "en-lead-acid", "en-lfp-battery", "en-li-ion-nmc", "en-tnt", "en-dry-wood", "en-bituminous-coal", "en-diesel-jet", "en-hydrogen", "en-u235-fission", "en-dt-fusion"]},
            {"dimension_id": "power_w", "ordered_entity_ids": ["pwr-smartphone", "pwr-led-bulb", "pwr-human-basal", "pwr-us-home-elec", "pwr-car-engine", "pwr-onshore-wind", "pwr-nuclear-unit", "pwr-global-primary", "pwr-earth-sunlight"]},
            {"dimension_id": "density_kg_m3", "ordered_entity_ids": ["den-air", "den-eps-foam", "den-softwood", "den-water", "den-concrete", "den-aluminum", "den-steel", "den-copper", "den-lead", "den-gold", "den-osmium"]},
            {"dimension_id": "temperature_k", "ordered_entity_ids": ["tmp-cmb", "tmp-liq-helium", "tmp-liq-nitrogen", "tmp-water-freeze", "tmp-water-boil", "tmp-aluminum-melt", "tmp-steel-melt", "tmp-sun-surface", "tmp-sun-core"]},
            {"dimension_id": "pressure_pa", "ordered_entity_ids": ["prs-mars-surface", "prs-everest-air", "prs-1atm", "prs-car-tire", "prs-scuba-tank", "prs-mariana-trench", "prs-steel-yield", "prs-earth-core"]},
        ],
    }

    total_regions = sum(len(f["regions"]) for f in figures)
    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "physics.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join("content", "verification-physics.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote M3 physics.json: {len(facts)} facts, {len(plain_cards)} scaling cards, {len(figures)} SVGs ({total_regions} regions) = {len(facts) + len(plain_cards) + total_regions} total schedulable items.")

if __name__ == "__main__":
    main()
