import streamlit as st
import requests
import matplotlib.pyplot as plt
import numpy as np
import re
import os
import io
import json
import random
from gtts import gTTS
from duckduckgo_search import DDGS

# ============================================================
# 1. PAGE CONFIG & STYLING
# ============================================================
st.set_page_config(page_title="H2 Feynman Bot", page_icon="⚛️", layout="centered")

st.markdown("""
<style>
    /* Make equations look better */
    .st {
        font-size: 1.1em;
        margin: 10px 0;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 5px;
        border-left: 4px solid #4CAF50;
    }
    
    /* Improve text readability */
    .stMarkdown {
        font-size: 16px;
        line-height: 1.6;
    }
    
    /* Quiz styling */
    .quiz-question {
        background-color: #f0f7ff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        margin-bottom: 20px;
    }
    
    .quiz-option {
        background-color: white;
        padding: 12px;
        margin: 8px 0;
        border-radius: 8px;
        border: 1px solid #ddd;
        cursor: pointer;
    }
    
    .quiz-option:hover {
        background-color: #e8f4fd;
        border-color: #2196F3;
    }
    
    .quiz-option.selected {
        background-color: #e3f2fd;
        border-color: #2196F3;
        border-width: 2px;
    }
    
    .quiz-feedback {
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
    }
    
    .correct-feedback {
        background-color: #e8f5e9;
        border-left: 4px solid #4CAF50;
    }
    
    .incorrect-feedback {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. INSTRUCTIONS & CONSTANTS
# ============================================================

SEAB_H2_MASTER_INSTRUCTIONS = """
**Identity:** Richard Feynman. Tutor for Singapore H2 Physics (9478).

**CORE DIRECTIVES:**
1.  **Socratic Method:** Ask ONE simple question at a time but do not ask more than 4 questions for each concept. Do not solve immediately. Be encouraging and enthusiastic.
2.  **Formatting:**
    * Use LaTeX for math: $F=ma$ (inline) or $$E=mc^2$$ (block).
    * **Bold** key terms.
3.  **Tools:**
    * **Graphs:** Write `python` code using `matplotlib` and `numpy`.
    * **Images:** Use `[IMAGE: concise search query]` to show diagrams. Example: "Here is the setup: [IMAGE: youngs double slit diagram]"

**STRICTLY adhere to SEAB H2 Physics 9478 syllabus.**
"""

USER_LEVEL_INSTRUCTIONS = {
    "Beginner": "**Beginner:** Simple steps, everyday analogies. Avoid complex jargon initially.",
    "Intermediate": "**Intermediate:** Balance concepts and math. Assume basic knowledge.",
    "Advance": "**Advanced:** Focus on deep concepts and derivations, skip basics."
}

# Quiz difficulty levels
QUIZ_LEVELS = {
    "Basic": "Basic: Testing fundamental concepts with simple calculations and diagrams",
    "Intermediate": "Intermediate: Applying concepts to solve problems with moderate complexity",
    "Advanced": "Advanced: Complex problem-solving, derivations, and analysis"
}

# ============================================================
# 3. SYLLABUS DATA (Shared between Quiz and Chat)
# ============================================================

physics_topics = [
    "General / Any",
    "1. Quantities and Measurement",
    "2. Forces and Moments",
    "3. Motion and Forces",
    "4. Energy and Fields",
    "5. Projectile Motion",
    "6. Collisions",
    "7. Circular Motion",
    "8. Gravitational Fields",
    "9. Oscillations",
    "10. Wave Motion",
    "11. Superposition",
    "12. Temperature and Ideal Gases",
    "13. Thermodynamic Systems",
    "14. Electric Fields",
    "15. Currents",
    "16. Circuits",
    "17. Electromagnetic Forces",
    "18. Electromagnetic Induction",
    "19. Quantum Physics",
    "20. Nuclear Physics"
]

# Syllabus details shared between quiz and chat
syllabus_details = {
    "1. Quantities and Measurement": "Candidates should be able to: (a) recall and use the following SI base quantities and their units: mass (kg), length (m), time (s), current (A), temperature (K), amount of substance (mol); (b) recall and use the following prefixes and their symbols to indicate decimal sub-multiples or multiples of both base and derived units: pico (p), nano (n), micro (μ), milli (m), centi (c), deci (d), kilo (k), mega (M), giga (G), tera (T); (c) express derived units as products or quotients of the SI base units and use the named units listed in 'Summary of Key Quantities, Symbols and Units' as appropriate; (d) use SI base units to check the homogeneity of physical equations; (e) make reasonable estimates of physical quantities included within the syllabus; (f) show an understanding of the distinction between random errors and systematic errors (including zero error) which limit precision and accuracy; (g) assess the uncertainty in derived quantities by adding absolute or relative (i.e. fractional or percentage) uncertainties or by numerical substitution (rigorous statistical treatment is not required); (h) distinguish between scalar and vector quantities, and give examples of each; (i) add and subtract coplanar vectors; (j) represent a vector as two perpendicular components.",
    
    "2. Forces and Moments": "Candidates should be able to: (a) describe the forces on a mass, charge and current-carrying conductor in gravitational, electric and magnetic fields, as appropriate; (b) show a qualitative understanding of forces including normal force, buoyant force (upthrust), frictional force and viscous force, e.g. air resistance. (knowledge of the concepts of coefficients of friction and viscosity is not required); (c) recall and apply Hooke's law ( \(F = kx\) , where \(k\) is the force constant) to new situations or to solve related problems; (d) define and apply the moment of a force and the torque of a couple; (e) show an understanding that a couple is a pair of forces which tends to produce rotation only; (f) show an understanding that the weight of a body may be taken as acting at a single point known as its centre of gravity; (g) apply the principle of moments to new situations or to solve related problems; (h) show an understanding that, when there is no resultant force and no resultant torque, a system is in equilibrium; (i) use free-body diagrams and vector triangles to represent forces on bodies that are in rotational and translational equilibrium.",
    
    "3. Motion and Forces": "Candidates should be able to: (a) show an understanding of and use the terms position, distance, displacement, speed, velocity and acceleration; (b) use graphical methods to represent distance, displacement, speed, velocity and acceleration; (c) identify and use the physical quantities from the gradients of position-time or displacement-time graphs and areas under and gradients of velocity-time graphs, including cases of non-uniform acceleration; (d) derive, from the definitions of velocity and acceleration, equations which represent uniformly accelerated motion in a straight line; (e) solve problems using equations which represent uniformly accelerated motion in a straight line, e.g. for bodies falling vertically without air resistance in a uniform gravitational field; (f) show an understanding that mass is the property of a body which resists change in motion (inertia); (g) define and use linear momentum as the product of mass and velocity; (h) state and apply each of Newton's laws of motion: 1st law: a body at rest will stay at rest, and a body in motion will continue to move at constant velocity, unless acted on by a resultant external force; 2nd law: the rate of change of momentum of a body is (directly) proportional to the resultant force acting on the body and is in the same direction as the resultant force; 3rd law: the force exerted by one body on a second body is equal in magnitude and opposite in direction to the force simultaneously exerted by the second body on the first body; (i) recall the relationship resultant force \(F = ma\) , for a body of constant mass, and use this to solve problems.",
    
    "4. Energy and Fields": "Candidates should be able to: (a) show an understanding that physical systems can store energy, and that energy can be transferred from one store to another; (b) give examples of different energy stores and energy transfers, and apply the principle of conservation of energy to solve problems; (c) show an understanding that work is a mechanical transfer of energy, and define and use work done by a force as the product of the force and displacement in the direction of the force; (d) derive, from the definition of work done by a force and the equations for uniformly accelerated motion in a straight line, the equation \(E_{\mathrm{k}} = \frac{1}{2} m\nu^{2}\); (e) recall and use the equation \(E_{\mathrm{k}} = \frac{1}{2} m\nu^{2}\) to solve problems; (f) show an understanding of the concept of a field as a region of space in which bodies may experience a force associated with the field; (g) define gravitational field strength at a point as the gravitational force per unit mass on a mass placed at that point, and define electric field strength at a point as the electric force per unit charge on a positive charge placed at that point; (h) represent gravitational fields and electric fields by means of field lines (e.g. for uniform and radial field patterns), and show an understanding of the relationship between equipotential surfaces and field lines; (i) show an understanding that the force on a mass in a gravitational field (or the force on a charge in an electric field) acts along the field lines, and the work done by the field in moving the mass (or charge) is equal to the negative of the change in potential energy; (j) distinguish between gravitational potential energy, electric potential energy and elastic potential energy; (k) recall that the elastic potential energy stored in a deformed material is given by the area under its force-extension graph and use this to solve problems; (l) define power as the rate of energy transfer; (m) show an understanding that mechanical power is the product of a force and velocity in the direction of the force; (n) show an appreciation for the implications of energy losses in practical devices and solve problems using the concept of efficiency of an energy transfer as the ratio of useful energy output to total energy input.",
    
    "5. Projectile Motion": "Candidates should be able to: (a) describe and use the concept of weight as the force experienced by a mass in a gravitational field; (b) describe and explain motion due to a uniform velocity in one direction and a uniform acceleration in a perpendicular direction; (c) derive, from the definition of work done by a force, the equation \(\Delta E_{\mathrm{p}} = mg\Delta h\) for gravitational potential energy changes in a uniform gravitational field (e.g. near the Earth's surface); (d) recall and use the equation \(\Delta E_{\mathrm{p}} = mg\Delta h\) to solve problems; (e) describe qualitatively, with reference to forces and energy, the motion of bodies falling in a uniform gravitational field with air resistance, including the phenomenon of terminal velocity.",
    
    "6. Collisions": "Candidates should be able to: (a) recall that impulse is given by the area under the force-time graph for a body and use this to solve problems; (b) state the principle of conservation of momentum; (c) apply the principle of conservation of momentum to solve simple problems including inelastic and (perfectly) elastic interactions between two bodies in one dimension (knowledge of the concept of coefficient of restitution is not required); (d) show an understanding that, for a (perfectly) elastic collision between two bodies, the relative speed of approach is equal to the relative speed of separation; (e) show an understanding that, whilst the momentum of a closed system is always conserved in interactions between bodies, some change in kinetic energy usually takes place.",
    
    "7. Circular Motion": "Candidates should be able to: (a) express angular displacement in radians; (b) show an understanding of and use the concept of angular velocity; (c) recall and use \(\nu = r\omega\) to solve problems; (d) show an understanding of centripetal acceleration in the case of uniform motion in a circle, and qualitatively describe motion in a curved path (arc) as due to a resultant force that is both perpendicular to the motion and centripetal in direction; (e) recall and use centripetal acceleration \(a = r\omega^2\) , and \(a = \frac{\nu^2}{r}\) to solve problems; (f) recall and use \(F = mr\omega^2\) , and \(F = \frac{mv^2}{r}\) to solve problems.",
    
    "8. Gravitational Fields": "Candidates should be able to: (a) recall and use Newton's law of gravitation in the form \(F = G\frac{m_1m_2}{r^2}\); (b) derive, from Newton's law of gravitation and the definition of gravitational field strength, the field strength due to a point mass, \(g = G\frac{M}{r^2}\); (c) recall and use \(g = G\frac{M}{r^2}\) for the gravitational field strength due to a point mass to solve problems; (d) show an understanding that near the surface of the Earth, gravitational field strength is approximately constant and equal to the acceleration of free fall; (e) define gravitational potential at a point as the work done per unit mass by an external force in bringing a small test mass from infinity to that point; (f) solve problems using the equation \(\phi = -G\frac{M}{r}\) for the gravitational potential in the field due to a point mass; (g) show an understanding that the gravitational potential energy of a system of two point masses is \(U_G = -G\frac{Mm}{r}\); (h) recall that gravitational field strength at a point is equal to the negative potential gradient at that point and use this to solve problems; (i) analyse problems related to escape velocity by considering energy stores and transfers; (j) analyse circular orbits in inverse square law fields by relating the gravitational force to the centripetal acceleration it causes; (k) show an understanding of satellites in geostationary orbit and their applications.",
    
    "9. Oscillations": "Candidates should be able to: (a) describe simple examples of free oscillations, where particles periodically return to an equilibrium position without gaining energy from or losing energy to the environment; (b) investigate the motion of an oscillator using experimental and graphical methods; (c) show an understanding of and use the terms amplitude, period, frequency, angular frequency, phase and phase difference and express the period in terms of both frequency and angular frequency; (d) show an understanding that \(a = - \omega^2 x\) is the defining equation of simple harmonic motion, where acceleration is (directly) proportional to displacement from an equilibrium position and acceleration is always directed towards the equilibrium position; (e) recognise and use \(x = x_0 \sin \omega t\) as a solution to the equation \(a = - \omega^2 x\); (f) recognise and use the equations \(\nu = \nu_0\cos \omega t\) and \(\nu = \pm \omega \sqrt{(x_0^2 - x^2)}\); (g) describe, with graphical illustrations, the relationships between displacement, velocity and acceleration during simple harmonic motion; (h) describe the interchange between kinetic and potential energy during simple harmonic motion; (i) describe practical examples of damped oscillations, with particular reference to the effects of the degree of damping (light/under, critical, heavy/over), and to the importance of critical damping in applications such as a car suspension system; (j) describe graphically how the amplitude of a forced oscillation changes with driving frequency, resulting in maximum amplitude at resonance when the driving frequency is close to or at the natural frequency of the system; (k) show a qualitative understanding of the effects of damping on the frequency response and sharpness of the resonance; (l) describe practical examples of forced oscillations and resonance, and show an appreciation that there are some circumstances in which resonance is useful, and other circumstances in which resonance should be avoided.",
    
    "10. Wave Motion": "Candidates should be able to: (a) show an understanding that mechanical waves involve the oscillations of particles within a material medium, such as a string or a fluid, and electromagnetic waves involve the oscillations of electromagnetic fields in space and time; (b) show an understanding of and use the terms displacement, amplitude, period, frequency, phase, phase difference, wavelength and speed; (c) deduce, from the definitions of speed, frequency and wavelength, the equation \(\nu = f\lambda\); (d) recall and use the equation \(\nu = f\lambda\); (e) analyse and interpret graphical representations of transverse and longitudinal waves with respect to variations in time and position (space); (f) show an understanding that energy is transferred due to a progressive wave without matter being transferred; (g) recall and use the term intensity as the power transferred (radiated) by a wave per unit area, and the relationship intensity \(\propto\) (amplitude) for a progressive wave; (h) show an understanding of and apply the concept, that the intensity of a wave from a point source and travelling without loss of energy obeys an inverse square law to solve problems; (i) show an understanding that polarisation is a phenomenon associated with transverse waves; (j) recall and use Malus' law (intensity \(\propto\) cos²θ) to calculate the amplitude and intensity of a plane-polarised electromagnetic wave after transmission through a polarising filter.",
    
    "11. Superposition": "Candidates should be able to: (a) explain and use the principle of superposition in simple applications; (b) show an understanding of experiments which demonstrate standing (stationary) waves using microwaves, stretched strings and air columns; (c) explain the formation of a standing (stationary) wave using a graphical method, and identify nodes and antinodes, differentiating between pressure and displacement nodes and antinodes for sound waves; (d) determine the wavelength of sound using standing (stationary) waves; (e) show an understanding of the terms diffraction, interference, coherence, phase difference and path difference; (f) show an understanding of phenomena which demonstrate two-source interference using water waves, sound waves, light and microwaves; (g) show an understanding of the conditions required for two-source interference fringes to be observed; (h) recall and use the equation \(\frac{ax}{D} = \lambda\) to solve problems for double-slit interference, where \(a\) is the slit separation and \(x\) is the fringe separation; (i) recall and use the equation \(a \sin \theta = n\lambda\) to solve problems involving the principal maxima of a diffraction grating, where \(a\) is the slit separation; (j) describe the use of a diffraction grating to determine the wavelength of light (knowledge of the structure and use of a spectrometer is not required); (k) show an understanding of phenomena which demonstrate diffraction through a single slit or aperture, or across an edge, such as the diffraction of water waves in a ripple tank with both a wide gap and a narrow gap, or the diffraction of sound waves from loudspeakers or around corners; (l) recall and use the equation \(b \sin \theta = \lambda\) to solve problems involving the positions of the first minima for diffraction through a single slit of width \(b\); (m) recall and use the Rayleigh criterion \(\theta \approx \frac{\lambda}{b}\) for the resolving power of a single aperture, where \(b\) is the width of the aperture.",
    
    "12. Temperature and Ideal Gases": "Candidates should be able to: (a) show an understanding that a thermodynamic scale of temperature has an absolute zero and is independent of the property of any particular substance; (b) convert temperatures measured in degrees Celsius to kelvin: \(T / K = T / ^{\circ}C + 273.15\); (c) recall and use the equation of state for an ideal gas expressed as \(\rho V = NkT\), where \(N\) is the number of particles; (d) state that one mole of any substance contains \(6.02 \times 10^{23}\) particles, and use the Avogadro constant \(N_{\mathrm{A}} = 6.02 \times 10^{23} \mathrm{~mol}^{-1}\) as well as the relationship \(Nk = nR\) between the Boltzmann constant and the molar gas constant, where \(n\) is the number of moles and \(N = nN_{\mathrm{A}}\); (e) state the basic assumptions of the kinetic theory of gases; (f) explain how the random motion of gas particles exerts mechanical pressure and hence derive, using the definition of pressure as force per unit area, the relationship \(\rho V = \frac{1}{3} Nm\left\langle c^2 \right\rangle\) (a simple model considering one- dimensional collisions and then extending to three dimensions using \(\left\langle c_x^2 \right\rangle = \frac{1}{3}\left\langle c^2 \right\rangle\) is sufficient); (g) recall and use the relationship that the mean translational kinetic energy of a particle of an ideal gas is (directly) proportional to the thermodynamic temperature (i.e. \(\frac{1}{2} m\left\langle c^2 \right\rangle = \frac{3}{2} kT\)) to solve problems.",
    
    "13. Thermodynamic Systems": "Candidates should be able to: (a) show an understanding that the macroscopic state of a system determines the internal energy of the system, and that internal energy can be expressed as the sum of a random distribution of microscopic kinetic and potential energies associated with the particles of the system; (b) show an understanding that the thermodynamic temperature of a system is (directly) proportional to the mean microscopic kinetic energy of particles; (c) show an understanding that when two systems are placed in thermal contact, energy is transferred (by heating) from the system at higher temperature to the system at lower temperature, until they reach the same temperature and achieve thermal equilibrium (i.e. no net energy transfer); (d) show an understanding of the difference between the work done by a gas and the work done on a gas, and calculate the work done by a gas in expanding against a constant external pressure: \(W = \rho \Delta V\); (e) recall and apply the zeroth law of thermodynamics that if two systems are both in thermal equilibrium with a third system, then they are also in thermal equilibrium with each other; (f) recall and apply the first law of thermodynamics, \(\Delta U = Q + W\), that the increase in internal energy of a system is equal to the sum of the energy transferred to the system by heating and the work done on the system; (g) define and use the concepts of specific heat capacity and specific latent heat.",
    
    "14. Electric Fields": "Candidates should be able to: (a) recall and use Coulomb's law in the form \(F = \frac{1}{4\pi\epsilon_0}\frac{Q_1Q_2}{r^2}\) for the electric force between two point charges in free space or air; (b) recall and use \(E = \frac{1}{4\pi\epsilon_0}\frac{Q}{r^2}\) for the electric field strength due to a point charge, in free space or air, to solve problems; (c) define electric potential at a point as the work done per unit charge by an external force in bringing a small positive test charge from infinity to that point; (d) use the equation \(V = \frac{1}{4\pi\epsilon_0}\frac{Q}{r}\) for the electric potential in the field due to a point charge, in free space or air; (e) show an understanding that the electric potential energy of a system of two point charges is \(U_{E} = \frac{1}{4\pi\epsilon_{0}}\frac{Q_{1}Q_{2}}{r}\); (f) recall that electric field strength at a point is equal to the negative potential gradient at that point and use this to solve problems; (g) calculate the field strength of the uniform electric field between charged parallel plates in terms of the potential difference and plate separation; (h) calculate the force on a charge in a uniform electric field; (i) describe the effect of a uniform electric field on the motion of a charged particle; (j) define capacitance as the ratio of the charge stored to the potential difference and use \(C = \frac{Q}{V}\) to solve problems; (k) recall that the electric potential energy stored in a capacitor is given by the area under the graph of potential difference against charge stored, and use this and the equations \(U = \frac{1}{2} QV\), \(U = \frac{1}{2}\frac{Q^2}{C}\) and \(U = \frac{1}{2} CV^2\) to solve problems.",
    
    "15. Currents": "Candidates should be able to: (a) show an understanding that electric current is the rate of flow of charge and solve problems using \(I = \frac{Q}{t}\); (b) derive and use the equation \(I = nAvq\) for a current-carrying conductor, where \(n\) is the number density of charge carriers and \(v\) is the drift velocity; (c) recall and solve problems using the equation for potential difference in terms of electrical work done per unit charge, \(V = \frac{W}{Q}\); (d) recall and solve problems using the equations for electrical power \(P = VI\), \(P = I^2 R\) and \(P = \frac{V^2}{R}\); (e) distinguish between electromotive force (e.m.f.) and potential difference (p.d.) using energy considerations; (f) show an understanding of and use the terms period, frequency, peak value and root-mean-square (r.m.s.) value as applied to an alternating current or voltage; (g) represent a sinusoidal alternating current or voltage by an equation of the form \(x = x_0 \sin \omega t\); (h) deduce that the mean power in a resistive load is half the maximum (peak) power for a sinusoidal alternating current; (i) distinguish between r.m.s. and peak values, and recall and use \(I_{\text{rms}} = \frac{I_0}{\sqrt{2}}\) and \(V_{\text{rms}} = \frac{V_0}{\sqrt{2}}\) for the sinusoidal case; (j) explain the use of a single diode for the half- wave rectification of an alternating current.",
    
    "16. Circuits": "Candidates should be able to: (a) recall and use appropriate circuit symbols; (b) draw and interpret circuit diagrams containing sources, switches, resistors (fixed and variable), ammeters, voltmeters, lamps, thermistors, light-dependent resistors, diodes, capacitors and any other type of component referred to in the syllabus; (c) define the resistance of a circuit component as the ratio of the potential difference across the component to the current in it, and solve problems using the equation \(V = IR\); (d) recall and solve problems using the equation relating resistance to resistivity, length and cross-sectional area, \(R = \frac{\rho l}{A}\); (e) sketch and interpret the \(I - V\) characteristics of various electrical components in a d.c. circuit, such as an ohmic resistor, a semiconductor diode, a filament lamp and a negative temperature coefficient (NTC) thermistor; (f) explain the temperature dependence of the resistivity of typical metals (e.g. in a filament lamp) and semiconductors (e.g. in an NTC thermistor) in terms of the drift velocity and number density of charge carriers respectively; (g) show an understanding of the effects of the internal resistance of a source of e.m.f. on the terminal potential difference and output power; (h) solve problems using the formula for the combined resistance of two or more resistors in series; (i) solve problems using the formula for the combined resistance of two or more resistors in parallel; (j) solve problems involving series and parallel arrangements of resistors for one source of e.m.f., including potential divider circuits which may involve NTC thermistors and light-dependent resistors; (k) solve problems using the formulae for the combined capacitance of two or more capacitors in series and in parallel; (l) describe and represent the variation with time, of quantities like current, charge and potential difference, for a capacitor that is charging or discharging through a resistor, using equations of the form \(x = x_0 e^{-\frac{t}{\tau}}\) or \(x = x_0[1 - e^{-\frac{t}{\tau}}]\), where \(\tau = RC\) is the time constant.",
    
    "17. Electromagnetic Forces": "Candidates should be able to: (a) show an understanding that a magnetic field is an example of a field of force produced either by current-carrying conductors or by permanent magnets; (b) sketch magnetic field lines due to currents in a long straight wire, a flat circular coil and a long solenoid; (c) use \(B = \frac{\mu_0 I}{2\pi d}\), \(B = \frac{\mu_0 NI}{2r}\) and \(B = \mu_0 nI\) for the magnetic flux densities of the fields due to currents in a long straight wire, a flat circular coil and a long solenoid respectively; (d) show an understanding that the magnetic field due to a solenoid may be influenced by the presence of a ferrous core; (e) show an understanding that a current-carrying conductor placed in a magnetic field might experience a force; (f) recall and solve problems using the equation \(F = BIl\sin \theta\), with directions as interpreted by Fleming's left-hand rule; (g) define magnetic flux density as the force acting per unit current per unit length on a conductor placed perpendicular to the magnetic field; (h) show an understanding of how the force on a current-carrying conductor can be used to measure the magnetic flux density of a magnetic field using a current balance; (i) explain the forces between current-carrying conductors and predict the direction of the forces; (j) predict the direction of the force on a charge moving in a uniform magnetic field; (k) recall and solve problems using the equation \(F = BQv\sin \theta\); (l) describe and analyse deflections of beams of charged particles by uniform electric fields and uniform magnetic fields; (m) explain how perpendicular electric and magnetic fields can be used in velocity selection for charged particles.",
    
    "18. Electromagnetic Induction": "Candidates should be able to: (a) define magnetic flux as the product of magnetic flux density and the cross-sectional area perpendicular to the direction of the magnetic flux density; (b) show an understanding of and use the concept of magnetic flux linkage; (c) recall and use \(\Phi = BA\) and \(N\Phi = NBA\) to solve problems, where \(N\) is the number of turns; (d) infer from appropriate experiments on electromagnetic induction: (i) that a changing magnetic flux can induce an e.m.f., (ii) that the direction of the induced e.m.f. opposes the change producing it, (iii) the factors affecting the magnitude of the induced e.m.f.; (e) recall and solve problems using Faraday's law of electromagnetic induction and Lenz's law; (f) explain simple applications of electromagnetic induction; (g) show an understanding of the principle of operation of a simple iron-core transformer and recall and solve problems using \(\frac{N_s}{N_p} = \frac{V_s}{V_p} = \frac{I_p}{I_s}\) for an ideal transformer.",
    
    "19. Quantum Physics": "Candidates should be able to: (a) show an understanding that the existence of a threshold frequency in the photoelectric effect provides evidence that supports the particulate nature of electromagnetic radiation while phenomena such as interference and diffraction provide evidence that supports its wave nature; (b) state that a photon is a quantum of electromagnetic radiation, and recall and use the equation \(E = hf\) for the energy of a photon to solve problems, where \(h\) is the Planck constant; (c) show an understanding that while a photon is massless, it has a momentum given by \(p = \frac{E}{c}\) and \(p = \frac{h}{\lambda}\) where \(c\) is the speed of light in free space; (d) show an understanding that electron diffraction and double-slit interference of single particles provide evidence that supports the wave nature of particles; (e) recall and use the equation \(\lambda = \frac{h}{p}\) for the de Broglie wavelength to solve problems; (f) show an understanding that the state of a particle can be represented as a wavefunction \(\psi\), e.g. for an electron cloud in an atom, and that the square of the wavefunction amplitude \(\left|\psi \right|^2\) is the probability density function (including calculation of normalisation factors for square and sinusoidal wavefunctions); (g) show an understanding that the principle of superposition applies to the wavefunctions describing a particle's position, leading to standing wave solutions for a particle in a box and phenomena such as single-particle interference in double-slit experiments; (h) show an understanding that the Heisenberg position-momentum uncertainty principle \(\Delta x\Delta p \geq h\) relates to the necessity of a spread of momenta for localised particles, and apply this to solve problems; (i) show an understanding of standing wave solutions \(\psi_n\) for the wavefunction of a particle in a one-dimensional infinite square well potential; (j) solve problems using \(E_n = \frac{h^2}{8mL^2} n^2\) for the allowed energy levels of a particle of mass \(m\) in a one-dimensional infinite square well of width \(L\); (k) show an understanding of the existence of discrete electronic energy levels for the electron's wavefunction in isolated atoms (e.g. atomic hydrogen) and deduce how this leads to the observation of spectral lines; (l) distinguish between emission and absorption line spectra; (m) solve problems involving photon absorption or emission during atomic energy level transitions.",
    
    "20. Nuclear Physics": "Candidates should be able to: (a) infer from the results of the Rutherford \(\alpha\) -particle scattering experiment the existence and small size of the atomic nucleus; (b) distinguish between nucleon number (mass number) and proton number (atomic number); (c) show an understanding that an element can exist in various isotopic forms, each with a different number of neutrons in the nucleus, and use the notation \(\frac{1}{2} X\) for the representation of nuclides; (d) show an understanding of the spontaneous and random nature of nuclear decay; (e) infer the random nature of radioactive decay from the fluctuations in count rate; (f) show an understanding of the origin and significance of background radiation; (g) show an understanding of the nature and properties of \(\alpha\), \(\beta\) and \(\gamma\) radiations (knowledge of positron emission is not required); (h) define the terms activity and decay constant and recall and solve problems using the equation \(A = \lambda N\); (i) infer and sketch the exponential nature of radioactive decay and solve problems using the relationship \(x = x_{0}e^{-\lambda t}\) where \(x\) could represent activity, number of undecayed particles or received count rate; (j) define and use half-life as the time taken for a quantity \(x\) to reduce to half its initial value; (k) solve problems using the relation \(\lambda = \frac{\ln 2}{t_1}\); (l) discuss qualitatively the applications (e.g. medical and industrial uses) and hazards of radioactivity based on: (i) half-life of radioactive materials, (ii) penetrating abilities and ionising effects of radioactive emissions; (m) represent simple nuclear reactions by nuclear equations of the form \(\frac{1}{2} N + \frac{1}{2} He \rightarrow \frac{17}{8} O + \frac{1}{4} H\); (n) state and apply to problem solving the concept that nucleon number, charge and mass- energy are all conserved in nuclear processes; (o) show an understanding of how the conservation laws for energy and momentum in \(\beta\) decay were used to predict the existence of the (anti)neutrino (knowledge of the antineutrino and the zoo of particles is not required); (p) show an understanding of the concept of mass defect; (q) recall and apply the equivalence between energy and mass as represented by \(E = mc^2\) to solve problems; (r) show an understanding of the concept of nuclear binding energy and its relation to mass defect; (s) sketch the variation of binding energy per nucleon with nucleon number; (t) explain the relevance of binding energy per nucleon to nuclear fusion and to nuclear fission."
}

# ============================================================
# 4. QUIZ FUNCTIONS (UNCHANGED from previous version)
# ============================================================

def generate_quiz_prompt(difficulty, topic_name, num_questions=20):
    """
    Generate a prompt for creating quiz questions WITHOUT image requirements.
    """
    # Get topic-specific guidance
    topic_guidance = syllabus_details.get(topic_name, "Cover key concepts from the official SEAB H2 Physics syllabus.")

    prompt = f"""Generate exactly {num_questions} H2 Physics questions for topic: {topic_name}
Difficulty: {difficulty}

SYLLABUS REQUIREMENTS:
{topic_guidance}

CRITICAL FORMATTING RULES:
1. Return ONLY a valid JSON array.
2. Each question MUST follow this EXACT structure:
{{
  "question_number": 1,
  "question_type": "mcq",
  "question": "Question text with LaTeX like $F=ma$",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "Option A",
  "explanation": "Detailed explanation with equations like $F=ma$"
}}

OR for open-ended:
{{
  "question_number": 2,
  "question_type": "open_ended",
  "question": "Calculate the force...",
  "options": [],
  "correct_answer": "10 N",
  "explanation": "Using $F=ma$..."
}}

SPECIFIC INSTRUCTIONS:
1. Mix: 70% MCQ (4 options each), 30% open-ended
2. NO image requirements - describe any diagrams in the question text
3. Use LaTeX for equations: $E=mc^2$ inline
4. Escape quotes: use backslash like \\" for quotes inside strings
5. NO additional text outside the JSON array
6. Number questions from 1 to {num_questions}

EXAMPLE FORMAT:
[
  {{
    "question_number": 1,
    "question_type": "mcq",
    "question": "What is Newton's second law?",
    "options": ["F = ma", "F = mg", "v = u + at", "s = ut + ½at²"],
    "correct_answer": "F = ma",
    "explanation": "Newton's second law states: $F = ma$"
  }}
]

NOW GENERATE {num_questions} QUESTIONS IN THIS EXACT FORMAT:
"""
    return prompt

import re
import json

def parse_quiz_response(response_text):
    """Parse AI response with robust handling of malformed JSON."""
    try:
        # Extract JSON array boundaries
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']')
        if start_idx == -1 or end_idx == -1:
            st.error("❌ No JSON array boundaries found ([ or ]) in response")
            with st.expander("🐞 Raw Response (First 1000 chars)", expanded=True):
                st.code(response_text[:1000], language="text")
            return None
        
        json_str = response_text[start_idx:end_idx + 1]
        
        # === CRITICAL FIX: Handle unescaped quotes safely ===
        # Instead of fragile regex, use character-by-character parsing
        def fix_unescaped_quotes(json_fragment):
            result = []
            in_string = False
            escape_next = False
            for i, char in enumerate(json_fragment):
                if escape_next:
                    result.append(char)
                    escape_next = False
                    continue
                
                if char == '\\':
                    result.append(char)
                    escape_next = True
                    continue
                
                if char == '"':
                    # Check if this quote is inside a key (before colon) or value (after colon)
                    # Simple heuristic: if previous non-whitespace char was : or { or , → likely start of value
                    prev_chars = ''.join(result[-10:]).rstrip()
                    if not in_string and (prev_chars.endswith(':') or prev_chars.endswith('{') or prev_chars.endswith(',')):
                        in_string = True
                        result.append(char)
                    elif in_string:
                        # Look ahead: if next non-whitespace is , } ] → this is end of string
                        next_chars = json_fragment[i+1:i+10].lstrip()
                        if next_chars.startswith((',', '}', ']')):
                            in_string = False
                            result.append(char)
                        else:
                            # Likely unescaped quote INSIDE string → escape it
                            result.append('\\"')
                    else:
                        result.append(char)
                else:
                    result.append(char)
            return ''.join(result)
        
        # Apply fixes
        fixed_json = fix_unescaped_quotes(json_str)
        fixed_json = re.sub(r",\s*([\]}])", r"\1", fixed_json)  # Remove trailing commas
        fixed_json = re.sub(r"'([^']+)':", r'"\1":', fixed_json)  # Fix single-quoted keys
        
        # Parse
        questions = json.loads(fixed_json)
        
        if not isinstance(questions, list):
            questions = [questions]
        
        # Validate structure
        validated = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                st.warning(f"⚠️ Skipping non-dict item #{i+1}")
                continue
            
            validated_q = {
                'question_number': int(q.get('question_number', i+1)),
                'question_type': str(q.get('question_type', 'mcq')).lower(),
                'question': str(q.get('question', f'Question {i+1}')).strip(),
                'options': [str(opt).strip() for opt in q.get('options', [])] if isinstance(q.get('options'), list) else [],
                'correct_answer': str(q.get('correct_answer', '')).strip(),
                'explanation': str(q.get('explanation', '')).strip()
            }
            validated.append(validated_q)
        
        st.success(f"✅ Successfully parsed {len(validated)} questions")
        return validated
        
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON parse error at line {e.lineno}, col {e.colno} (char {e.pos}): {e.msg}")
        
        # Show RAW input BEFORE any cleanup
        with st.expander("🐞 RAW INPUT (Before Parsing) - COPY THIS FOR DEBUGGING", expanded=True):
            st.subheader("Full raw response:")
            st.text(response_text)
            st.caption(f"Total length: {len(response_text)} characters")
        
        # Show problematic region
        if 'json_str' in locals() and len(json_str) > e.pos:
            char_start = max(0, e.pos - 80)
            char_end = min(len(json_str), e.pos + 80)
            st.subheader(f"Problem region (chars {char_start}-{char_end}):")
            st.code(json_str[char_start:char_end], language="text")
            st.caption("💡 Look for unescaped quotes like `\"text\"here\"` or missing commas")
        
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {type(e).__name__} - {e}")
        import traceback
        st.code(traceback.format_exc(), language="python")
        return None
def fix_json_string(json_str):
    """Fix common JSON formatting issues."""
    if not json_str:
        return json_str
    
    # Replace smart quotes with straight quotes
    json_str = json_str.replace('"', '"').replace('"', '"')
    
    # Fix unescaped quotes within strings
    lines = json_str.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Simple fix: replace unescaped quotes with escaped ones in string values
        if ':' in line and '"' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key_part = parts[0]
                value_part = parts[1]
                
                # Check if value is a string
                if value_part.strip().startswith('"'):
                    # Find the closing quote
                    if value_part.count('"') >= 2:
                        # Simple fix for common case
                        value_part = value_part.replace('\\"', '__TEMP__')
                        value_part = value_part.replace('"', '\\"')
                        value_part = value_part.replace('__TEMP__', '\\"')
                        # Remove double escaping
                        value_part = value_part.replace('\\\\"', '\\"')
                
                fixed_lines.append(f'{key_part}:{value_part}')
                continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def display_quiz_question(question_data, question_index):
    """Display a single quiz question with its components."""
    
    # DEFENSIVE CHECK: Ensure required keys exist
    if 'question_type' not in question_data:
        st.error(f"Question {question_index + 1} has invalid format (missing question_type).")
        return
    
    with st.container():
        st.markdown(f'<div class="quiz-question">', unsafe_allow_html=True)
        
        # Display question number and text
        st.subheader(f"Question {question_index + 1} of {len(st.session_state.quiz_questions)}")
        
        # Safely get question text
        question_text = question_data.get('question', f'Question {question_index + 1}')
        st.markdown(f"**{question_text}**")
        
        # Handle different question types
        if question_data['question_type'] == 'mcq':
            # Get options safely
            options = question_data.get('options', [])
            if not options or len(options) == 0:
                st.warning("This MCQ has no options.")
                options = ["Option A", "Option B", "Option C", "Option D"]
            
            # Display MCQ options
            selected_option = st.session_state.get(f'selected_option_{question_index}', None)
            
            for i, option in enumerate(options):
                option_key = f"option_{question_index}_{i}"
                if st.button(option, key=option_key, use_container_width=True):
                    st.session_state[f'selected_option_{question_index}'] = i
                    st.session_state[f'user_answer_{question_index}'] = option
                    st.rerun()
            
            # Check answer button
            if selected_option is not None:
                user_answer = options[selected_option]
                correct_answer = question_data.get('correct_answer', '')
                
                if st.button("Check Answer", key=f"check_{question_index}", type="primary"):
                    st.session_state[f'answered_{question_index}'] = True
                    st.rerun()
                
                if st.session_state.get(f'answered_{question_index}', False):
                    if user_answer == correct_answer:
                        st.success("✅ Correct!")
                    else:
                        st.error(f"❌ Incorrect. The correct answer is: {correct_answer}")
                    
                    # Show explanation
                    with st.expander("View Explanation"):
                        explanation = question_data.get('explanation', 'No explanation provided.')
                        st.markdown(f"**Explanation:** {explanation}")
        
        elif question_data['question_type'] == 'open_ended':
            # Open-ended question
            user_answer = st.text_input(
                f"Your answer (Question {question_index + 1}):",
                key=f"open_answer_{question_index}",
                placeholder="Enter your calculation or explanation..."
            )
            
            if st.button("Submit Answer", key=f"submit_{question_index}"):
                if user_answer:
                    st.session_state[f'user_answer_{question_index}'] = user_answer
                    st.session_state[f'answered_{question_index}'] = True
                    st.rerun()
            
            if st.session_state.get(f'answered_{question_index}', False):
                st.info(f"**Your answer:** {user_answer}")
                correct_answer = question_data.get('correct_answer', 'No correct answer provided.')
                st.success(f"**Correct answer:** {correct_answer}")
                
                with st.expander("View Explanation"):
                    explanation = question_data.get('explanation', 'No explanation provided.')
                    st.markdown(f"**Explanation:** {explanation}")
        
        else:
            st.error(f"Unknown question type: {question_data['question_type']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if question_index > 0:
                if st.button("← Previous", key=f"prev_{question_index}"):
                    st.session_state.current_question = question_index - 1
                    st.rerun()
        with col4:
            if question_index < len(st.session_state.quiz_questions) - 1:
                if st.button("Next →", key=f"next_{question_index}"):
                    st.session_state.current_question = question_index + 1
                    st.rerun()
        
        # Quiz progress
        st.progress((question_index + 1) / len(st.session_state.quiz_questions))
        st.caption(f"Progress: {question_index + 1}/{len(st.session_state.quiz_questions)}")

# ============================================================
# 5. AUTHENTICATION
# ============================================================
def check_login():
    """Check if user is logged in."""
    # If no password env var is set, skip login
    if "APP_PASSWORD" not in os.environ:
        return True 

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if st.session_state["authenticated"]:
        return True
    
    # Show login screen
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 H2 Physics Tutor")
        with st.form("login_form"):
            entered_password = st.text_input("Enter access password:", type="password")
            if st.form_submit_button("Login", type="primary"):
                stored_password = os.environ.get("APP_PASSWORD", "")
                if entered_password == stored_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
    
    st.stop()
    return False

if not check_login():
    st.stop()

# ============================================================
# 6. HELPER FUNCTIONS (UNCHANGED)
# ============================================================
@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Generate audio from text, skipping code/image tags."""
    try:
        # Clean text for speech
        clean_text = re.sub(r'```.*?```', 'I have generated a graph.', text, flags=re.DOTALL)
        clean_text = re.sub(r'\[IMAGE:.*?\]', 'Here is a diagram.', clean_text)
        clean_text = re.sub(r'\$.*?\$', 'equation', clean_text) # Skip reading raw latex
        
        if len(clean_text) > 5:
            tts = gTTS(text=clean_text, lang='en')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            return audio_fp
    except:
        pass
    return None

def google_search_api(query, api_key, cx):
    """Helper: Performs a single Google Search."""
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query, "cx": cx, "key": api_key,
            "searchType": "image", "num": 1, "safe": "active"
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["link"]
    except Exception:
        return None
    return None

def duckduckgo_search_api(query):
    """Helper: Fallback search using DuckDuckGo."""
    try:
        with DDGS(timeout=20) as ddgs:
            results = ddgs.images(keywords=query, region='wt-wt', safesearch='moderate')
            first_result = next(results, None)
            if first_result:
                return first_result['image']
    except Exception as e:
        return f"Search Error: {e}"
    return "No image found."

@st.cache_data(show_spinner=False)
def search_image(query):
    """MASTER FUNCTION: Google Key 1 -> Google Key 2 -> DuckDuckGo"""
    cx = os.environ.get("GOOGLE_CX")
    key1 = os.environ.get("GOOGLE_SEARCH_KEY")
    key2 = os.environ.get("GOOGLE_SEARCH_KEY_2")

    if key1 and cx:
        url = google_search_api(query, key1, cx)
        if url: return url
    if key2 and cx:
        url = google_search_api(query, key2, cx)
        if url: return url

    return duckduckgo_search_api(query)

def execute_plotting_code(code_snippet):
    """Execute plotting code safely."""
    try:
        plt.figure()
        local_env = {'plt': plt, 'np': np}
        exec(code_snippet, {}, local_env)
        st.pyplot(plt)
        plt.clf()
    except Exception as e:
        st.error(f"Graph Error: {e}")

def fix_latex(text):
    """Fix inconsistent LaTeX formatting for Streamlit."""
    # Convert \[ ... \] to $$ ... $$ (display math)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # Convert \( ... \) to $ ... $ (inline math)
    #text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    # Wrap standalone equations that use = and \ but miss $
    if '=' in text and '\\' in text and not '$' in text:
        text = re.sub(r'([a-zA-Zα-ωΑ-Ω_]+\s*=\s*\\[^ ]+.*?)(?=\s|$|\.|,)', r'$\1$', text)
    return text

def display_message(role, content, enable_voice=False):
    with st.chat_message(role):
        # 1. Extract Python Code
        code_blocks = []
        display_content = content
        for match in re.finditer(r'```python(.*?)```', content, re.DOTALL):
            code_blocks.append(match.group(1))
            display_content = display_content.replace(match.group(0), "")
        
        # 2. Extract Image Tags
        image_match = re.search(r'\[IMAGE:\s*(.*?)\]', display_content, re.IGNORECASE)
        image_query = None
        if image_match and role == "assistant":
            image_query = image_match.group(1)
            display_content = display_content.replace(image_match.group(0), "")
        
        # 3. Fix LaTeX
        display_content = fix_latex(display_content)
        
        # 4. Render Text
        st.markdown(display_content)
        
        # 5. Render Code/Graph
        if code_blocks and role == "assistant":
            execute_plotting_code(code_blocks[0])
            with st.expander("📊 Show Graph Code"):
                st.code(code_blocks[0], language='python')

        # 6. Render Image
        if image_match and role == "assistant" and image_query:
            image_result = search_image(image_query)
            if image_result and "Error" not in image_result:
                st.image(image_result, caption=f"Diagram: {image_query}")
            else:
                st.warning(f"⚠️ Image Search Failed: {image_result}")
        
        # 7. Audio
        if enable_voice and role == "assistant" and len(display_content.strip()) > 0:
            audio_bytes = generate_audio(content)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3')

# ============================================================
# 7. DEEPSEEK API CALL (UNCHANGED)
# ============================================================

def call_deepseek(messages, api_key, system_instruction):
    """Call DeepSeek API."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = "https://api.deepseek.com/chat/completions"
    
    # Prepend system instruction
    full_messages = [{"role": "system", "content": system_instruction}] + messages
    
    payload = {
        "model": "deepseek-chat",  # You can change this to "deepseek-coder" if needed
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 4000  # Increased for quiz generation
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ============================================================
# 8. MAIN APP UI WITH STRICT TOPIC ENFORCEMENT (OPTION 6)
# ============================================================
st.title("⚛️ JPJC H2Physics Feynman Bot")

# Sidebar Configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/4/42/Richard_Feynman_Nobel.jpg", width=150)
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.header("⚙️ Configuration")
    
    # DeepSeek API Key only
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if not deepseek_key:
        deepseek_key = st.text_input("DeepSeek API Key:", type="password", 
                                    help="Get your API key from https://platform.deepseek.com/api_keys")
    
    st.divider()
    
    # TOPIC SELECTION WITH ENFORCEMENT
    topic = st.selectbox(
        "Topic:",
        physics_topics,
        help="Select a specific topic for syllabus-aligned explanations"
    )
    
    # Show warning if General/Any is selected
    if topic == "General / Any":
        st.warning("⚠️ Select a specific topic for syllabus-aligned explanations")
    else:
        # Show learning outcomes preview
        with st.expander(f"📚 Syllabus Learning Outcomes for {topic}"):
            outcomes = syllabus_details.get(topic, "No specific outcomes available.")
            # Show first 300 chars with option to see more
            st.caption(outcomes[:300] + "..." if len(outcomes) > 300 else outcomes)
            st.caption(f"[{len(outcomes)} characters total - see full syllabus for details]")
    
    # USER LEVEL SELECTION
    user_level = st.select_slider(
        "Level:", 
        options=["Beginner", "Intermediate", "Advance"], 
        value="Intermediate"
    )
    
    enable_voice = st.toggle("🗣️ Read Aloud")
    
    st.divider()
    
    # ============================================
    # QUIZ SECTION (UNCHANGED)
    # ============================================
    st.header("📝 Quiz Generator")
    
    quiz_topic = st.selectbox(
        "Quiz Topic:",
        physics_topics,
        key="quiz_topic"
    )
    
    quiz_difficulty = st.selectbox(
        "Quiz Difficulty:",
        options=list(QUIZ_LEVELS.keys()),
        index=1,
        help=QUIZ_LEVELS["Intermediate"]
    )
    
    num_questions = st.slider("Number of questions:", 5, 30, 10)
    
    # --- Button with validation ---
    is_topic_general = (quiz_topic == "General / Any")
    
    if st.button("🎯 Generate Quiz", 
                 type="primary", 
                 use_container_width=True,
                 disabled=is_topic_general or not deepseek_key):
        
        if not deepseek_key:
            st.error("⚠️ Please provide a DeepSeek API Key first.")
        else:
            # Generate quiz prompt
            quiz_prompt = generate_quiz_prompt(quiz_difficulty, quiz_topic, num_questions)
            
            # Call DeepSeek to generate quiz
            with st.spinner(f"Generating {num_questions} {quiz_difficulty} quiz questions for {quiz_topic}..."):
                try:
                    # Prepare messages for quiz generation
                    quiz_messages = [
                        {"role": "user", "content": quiz_prompt}
                    ]
                    
                    # System instruction for quiz generation
                    quiz_system_instruction = """You are a strict JSON generator for H2 Physics quizzes. FOLLOW THESE RULES EXACTLY:
                    
                    1. OUTPUT ONLY a VALID JSON ARRAY. NO text before/after. NO markdown. NO comments.
                    2. Use DOUBLE quotes for keys/strings ONLY. NEVER use single quotes for keys.
                    3. NEVER use unescaped double quotes inside string values. 
                       ❌ BAD: "question": "What is "F=ma"?"
                       ✅ GOOD: "question": "What is F=ma?"
                       ✅ ALSO GOOD: "question": "What is \\"F=ma\\"?" (if you MUST quote)
                    4. Escape ALL internal double quotes with backslash: \\"
                    5. NO trailing commas before ] or }
                    6. MCQ options MUST be exactly 4 strings
                    7. Use LaTeX with single $: $F=ma$. NEVER wrap LaTeX in quotes like "$F=ma$"
                    
                    Example of CORRECT output:
                    [{"question_number":1,"question_type":"mcq","question":"Newton's second law states that force equals mass times acceleration $F=ma$.","options":["$F=ma$","$F=mg$","$v=u+at$","$W=Fd$"],"correct_answer":"$F=ma$","explanation":"Newton's second law is $F=ma$ where F is net force."}]
                    
                    VIOLATING THESE RULES WILL BREAK THE APP. OUTPUT ONLY THE JSON ARRAY."""

                    response = call_deepseek(quiz_messages, deepseek_key, quiz_system_instruction)

                    # ✅ INSERT DEBUG BLOCK HERE — THIS IS THE CORRECT SPOT
                    with st.expander("🐞 DEBUG: Raw Quiz Text (Before JSON Parsing)", expanded=True):
                        st.subheader("Full raw output:")
                        st.text(quiz_questions)
                        st.subheader("First 600 characters:")
                        st.code(quiz_questions[:600], language="text")
                        st.caption(f"Total length: {len(quiz_questions)} characters")

                    
                    # Parse the response
                    quiz_questions = parse_quiz_response(response)
                    
                    if quiz_questions and len(quiz_questions) > 0:
                        # Initialize quiz session state
                        st.session_state.quiz_questions = quiz_questions
                        st.session_state.quiz_active = True
                        st.session_state.current_question = 0
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_answers = {}
                        
                        # Clear any existing answers
                        for i in range(len(quiz_questions)):
                            st.session_state[f'answered_{i}'] = False
                            st.session_state[f'user_answer_{i}'] = None
                            st.session_state[f'selected_option_{i}'] = None
                        
                        st.success(f"✅ Generated {len(quiz_questions)} quiz questions!")
                        st.rerun()
                    else:
                        st.error("Failed to generate quiz questions. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error generating quiz: {e}")
    
    # Hint message
    if is_topic_general:
        st.info("🔍 Select a specific topic above to generate a targeted quiz.")
    
    if st.button("🧹 Clear Quiz", use_container_width=True):
        if 'quiz_questions' in st.session_state:
            del st.session_state.quiz_questions
        if 'quiz_active' in st.session_state:
            del st.session_state.quiz_active
        if 'current_question' in st.session_state:
            del st.session_state.current_question
        st.rerun()
    
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your JPJC Physics tutor. What concept shall we explore today?"}]
        st.rerun()

# Main content area
if 'quiz_active' in st.session_state and st.session_state.quiz_active:
    # Display quiz interface (UNCHANGED)
    st.header(f"📝 {quiz_topic} Quiz - {quiz_difficulty} Level")
    
    if 'quiz_questions' in st.session_state:
        current_q = st.session_state.current_question
        quiz_questions = st.session_state.quiz_questions
        
        # Quiz info bar
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Questions", len(quiz_questions))
        with col2:
            answered = sum(1 for i in range(len(quiz_questions)) 
                         if st.session_state.get(f'answered_{i}', False))
            st.metric("Answered", answered)
        with col3:
            correct = sum(1 for i in range(len(quiz_questions)) 
                         if st.session_state.get(f'answered_{i}', False) and 
                         st.session_state.get(f'user_answer_{i}') == quiz_questions[i]['correct_answer'])
            st.metric("Correct", correct)
        
        st.divider()
        
        # Display current question
        if current_q < len(quiz_questions):
            display_quiz_question(quiz_questions[current_q], current_q)
            
            # Quiz completion
            if answered == len(quiz_questions):
                st.balloons()
                st.success("🎉 Quiz Completed!")
                
                # Calculate final score
                final_score = (correct / len(quiz_questions)) * 100
                
                col1, col2, col3 = st.columns(3)
                with col2:
                    st.metric("Final Score", f"{final_score:.1f}%")
                
                # Review answers
                with st.expander("📊 Review All Answers"):
                    for i, q in enumerate(quiz_questions):
                        st.markdown(f"**Question {i+1}:** {q['question']}")
                        user_ans = st.session_state.get(f'user_answer_{i}', 'Not answered')
                        correct_ans = q['correct_answer']
                        
                        if user_ans == correct_ans:
                            st.success(f"✅ Your answer: {user_ans}")
                        else:
                            st.error(f"❌ Your answer: {user_ans}")
                            st.info(f"Correct answer: {correct_ans}")
                        st.divider()
        else:
            st.warning("Quiz questions not available.")
    else:
        st.info("No quiz active. Generate a quiz from the sidebar.")
    
    # Return to chat button
    if st.button("💬 Return to Chat", use_container_width=True):
        st.session_state.quiz_active = False
        st.rerun()

else:
    # ============================================
    # CHAT INTERFACE WITH STRICT TOPIC ENFORCEMENT
    # ============================================
    
    # Chat Logic
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant", 
            "content": f"""Hello! I'm your JPJC Physics tutor.

**To get started:**
1. **Select a specific topic** from the sidebar (not 'General / Any')
2. Choose your learning level (Beginner/Intermediate/Advanced)
3. Ask your physics question!

**Why select a topic?**
- Get explanations aligned with SEAB H2 Physics syllabus
- Focus on specific learning outcomes
- Receive exam-relevant examples and explanations

Ready to explore physics? Select a topic above! ⚛️"""
        }]

    # Display History
    for msg in st.session_state.messages:
        display_message(msg["role"], msg["content"], enable_voice)

    # Show guidance if no topic selected
    if topic == "General / Any":
        st.info("""
        **📚 Syllabus-Aligned Learning Required**
        
        To get accurate, exam-relevant explanations:
        1. **Select a specific topic** from the sidebar (not 'General / Any')
        2. Choose your difficulty level
        3. Ask your question
        
        Each topic includes specific SEAB learning outcomes that I'll reference in my explanations.
        """)

    # User Input - DISABLED when no topic selected
# User Input - DISABLED when no topic selected
chat_disabled = (topic == "General / Any")
placeholder = "Select a topic above to ask questions..." if chat_disabled else f"Ask about {topic}..."

if prompt := st.chat_input(placeholder, disabled=chat_disabled):
    
    if not deepseek_key:
        st.error("⚠️ Please provide a DeepSeek API Key in the sidebar.")
        st.stop()
    
    # Topic is already enforced by disabled chat input, but double-check
    if topic == "General / Any":
        st.error("❌ Please select a specific topic from the sidebar first.")
        st.stop()
    
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_message("user", prompt)
    
    # Get syllabus outcomes for the selected topic
    topic_outcomes = syllabus_details.get(topic, "")
    
    # Prepare System Prompt with Original Master Instruction
    level_instruction_text = USER_LEVEL_INSTRUCTIONS.get(user_level, "")
    
    current_instruction = f"""{SEAB_H2_MASTER_INSTRUCTIONS}

USER LEVEL: {user_level}
SELECTED TOPIC: {topic}

SYLLABUS LEARNING OUTCOMES FOR THIS TOPIC:
{topic_outcomes}

ADDITIONAL REQUIREMENTS:
1. Directly reference the specific learning outcomes above (a, b, c, etc.)
2. Tailor all explanations to {user_level} level understanding
3. Include exam-relevant examples when appropriate
4. Ensure all explanations align with the SEAB H2 Physics syllabus

{level_instruction_text}"""
    
    response_text = ""
    used_model = "DeepSeek"

    with st.spinner(f"Preparing syllabus-aligned explanation for {topic}..."):
        try:
            response_text = call_deepseek(st.session_state.messages, deepseek_key, current_instruction)
            used_model = "DeepSeek"
        except Exception as e:
            st.error(f"DeepSeek API Error: {e}. Please check your API key and internet connection.")
    
    if response_text:
        # Save and Display
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        display_message("assistant", response_text, enable_voice)
    elif not response_text:
        st.error("❌ API call failed. Please check your key or internet connection.")
