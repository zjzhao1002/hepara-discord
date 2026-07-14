import pdg
from pdg.errors import PdgAmbiguousValueError, PdgNoDataError
from pdg.particle import PdgParticle
from pdg.decay import PdgBranchingFraction
from typing import List

pdg_api = pdg.connect()

COMMON_ALIASES = {
  "gamma": ["photon", "light quantum"],
  "g": ["gluon"],
  "graviton": ["gravity quantum"],
  "W": ["W boson", "charged weak boson"],
  "Z": ["Z boson", "neutral weak boson"],
  "H": ["Higgs", "Higgs boson"],
  "Axions (A0) and Other Very Light Bosons": [
    "axion",
    "axions",
    "A0",
    "very light boson",
  ],
  "e": ["electron", "positron", "electron or positron"],
  "mu": ["muon", "antimuon", "muon or antimuon"],
  "tau": ["tau lepton", "antitau", "tau or antitau"],
  "nu_e": ["electron neutrino", "electron antineutrino"],
  "nu_mu": ["muon neutrino", "muon antineutrino"],
  "nu_tau": ["tau neutrino", "tau antineutrino"],
  "u": ["up", "u quark", "up quark"],
  "d": ["down", "d quark", "down quark"],
  "s": ["strange", "s quark", "strange quark"],
  "c": ["charm", "c quark", "charm quark"],
  "b": ["bottom", "beauty", "b quark", "bottom quark", "beauty quark"],
  "t": ["top", "truth", "t quark", "top quark", "truth quark"],
  "pi+-": ["charged pion", "charged pions", "pion plus or minus"],
  "pi0": ["neutral pion"],
  "eta": ["eta meson"],
  "K+-": ["charged kaon", "charged kaons", "kaon plus or minus"],
  "K0": ["neutral kaon"],
  "K(S)0": ["K short", "K-short", "short-lived neutral kaon"],
  "K(L)0": ["K long", "K-long", "long-lived neutral kaon"],
  "D+-": ["charged D meson", "D meson plus or minus"],
  "D0": ["neutral D meson"],
  "D_s()+-": ["charged D-s meson", "D strange meson"],
  "B+-": ["charged B meson", "B meson plus or minus"],
  "B0": ["neutral B meson"],
  "B_s()0": ["neutral B-s meson", "B strange meson"],
  "B_c()+": ["charged B-c meson", "B charm meson"],
  "J/psi(1S)": ["J/psi", "J psi", "J/psi meson", "charmonium ground state"],
  "Upsilon(1S)": ["Upsilon", "bottomonium ground state"],
  "p": ["proton"],
  "n": ["neutron"],
  "Lambda": ["Lambda baryon"],
  "Sigma+": ["positive Sigma baryon"],
  "Sigma0": ["neutral Sigma baryon"],
  "Sigma-": ["negative Sigma baryon"],
  "Xi0": ["neutral Xi baryon"],
  "Xi-": ["negative Xi baryon"],
  "Omega-": ["negative Omega baryon"],
}

GENERIC_ALIASES = {
  "pi": ["pion", "pions"],
  "K": ["kaon", "kaons"],
  "D": ["D meson", "D mesons"],
  "B": ["B meson", "B mesons"],
}

def _get_all_particle_names() -> List[str]:
    all_data = pdg_api.get_all(data_type_key='PART')
    all_particle_names =[]
    for data in all_data:
        all_particle_names.append(data.description)
    return all_particle_names

def _get_exact_name(name: str) -> str:
    all_exact_names = _get_all_particle_names()
    stripped_name = name.strip()
    normalized_name = stripped_name.casefold()

    for exact_name in all_exact_names:
        if stripped_name == exact_name:
            return exact_name

    for generic_name in GENERIC_ALIASES:
        if stripped_name == generic_name:
            return generic_name

    for exact_name in all_exact_names:
        if normalized_name == exact_name.strip().casefold():
            return exact_name

    for exact_name, aliases in COMMON_ALIASES.items():
        for alias in aliases:
            if normalized_name == alias.strip().casefold():
                return exact_name

    for generic_name, aliases in GENERIC_ALIASES.items():
        normalized_aliases = [alias.strip().casefold() for alias in aliases]
        if (normalized_name == generic_name.casefold()
                or normalized_name in normalized_aliases):
            return generic_name

    return ""

def _get_particle_by_name(name: str) -> PdgParticle | List[PdgParticle] | None:
    lookup_name = name.strip()
    try:
        return pdg_api.get_particle_by_name(lookup_name)
    except PdgAmbiguousValueError:
        return pdg_api.get_particles_by_name(lookup_name)
    except (ValueError, PdgNoDataError):
        exact_name = _get_exact_name(name)
        if not exact_name:
            return None
        try:
            return pdg_api.get_particle_by_name(exact_name)
        except PdgAmbiguousValueError:
            return pdg_api.get_particles_by_name(exact_name)
        except (ValueError, PdgNoDataError):
            return None

def get_particle_masses(name: str) -> str:
    particles = _get_particle_by_name(name)
    if particles is None:
        return f"Particle {name} was not found."

    results = ""
    if isinstance(particles, PdgParticle):
        for mass in particles.masses():
            results += f"{mass.description}: {mass.value} {mass.units}\n"
    elif isinstance(particles, List):
        for particle in particles:
            for mass in particle.masses():
                results += f"{mass.description}: {mass.value} {mass.units}\n"

    return results or f"Particle {name} has no mass data."

def get_particle_widths(name: str) -> str:
    particles = _get_particle_by_name(name)
    if particles is None:
        return f"Particle {name} was not found."
    
    results = ""
    if isinstance(particles, PdgParticle):
        for width in particles.widths():
            results += f"{width.description}: {width.value} {width.units}\n"
    elif isinstance(particles, List):
        for particle in particles:
            for width in particle.widths():
                results += f"{width.description}: {width.value} {width.units}\n"
    return results or f"Particle {name} has no width data."

def get_particle_lifetime(name: str) -> str:
    particles = _get_particle_by_name(name)
    if particles is None:
        return f"Particle {name} was not found."
    
    results = ""
    if isinstance(particles, PdgParticle):
        for lifetime in particles.lifetimes():
            results += f"{lifetime.description}: {lifetime.value} {lifetime.units}\n"
    elif isinstance(particles, List):
        for particle in particles:
            for lifetime in particle.lifetimes():
                results += f"{lifetime.description}: {lifetime.value} {lifetime.units}\n"
    return results or f"Particle {name} has no lifetime data."

def _get_child_particle_names(child: str) -> set[str]:
    names = {child.strip().casefold()}
    exact_name = _get_exact_name(child)
    if exact_name:
        names.add(exact_name.casefold())

    particles = _get_particle_by_name(child)
    if isinstance(particles, PdgParticle):
        names.add(particles.name.casefold())
    elif isinstance(particles, List):
        names.update(particle.name.casefold() for particle in particles)
    return names

def _select_branching_fractions(
        decay: PdgBranchingFraction,
        children: List[set[str]],
    ) -> str:
    product_names = set()
    for product in decay.decay_products:
        item = product.item
        product_names.add(item.name.casefold())
        product_names.update(particle.name.casefold() for particle in item.particles)

    if all(product_names.intersection(child_names) for child_names in children):
        if decay.display_value_text:
            return f"Channel: {decay.description}, Branching Fraction: {decay.display_value_text}\n"
        else:
            return f"Channel {decay.description} has no data for branching fraction.\n"
    return ""

def _get_particle_decays(particle: PdgParticle, children: List[str] | None) -> str:
    results = ""
    decays = particle.branching_fractions()
    if children is None: 
        for decay in decays:
            if decay.display_value_text:
                results += f"Channel: {decay.description}, Branching Fraction: {decay.display_value_text}\n"
            else:
                results += f"Channel {decay.description} has no data for branching fraction.\n"
    else:
        child_particle_names = [
            _get_child_particle_names(child) for child in children
        ]
        for decay in decays:
            results += _select_branching_fractions(decay, child_particle_names)
            
    return results

def get_particle_decays(parent: str, children: List[str] | None) -> str:
    results = ""
    particles = _get_particle_by_name(parent)
    if particles is None:
        return f"The parent particle ({parent}) was not found."
    
    if isinstance(particles, PdgParticle):
        results += _get_particle_decays(particles, children)
    elif isinstance(particles, List):
        for particle in particles:
            results += _get_particle_decays(particle, children)

    unique_lines = dict.fromkeys(results.splitlines())
    results = "".join(f"{line}\n" for line in unique_lines)
    
    if children is None:
        return results or f"Particle {parent} has no decay data"
    else:
        return results or f"Particle {parent} has no decay data with children: {" ".join(children)}"
    