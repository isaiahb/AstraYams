"""Publish recorded plant evidence for the generic Skill Studio research view.

No simulations or agent activity are invented here. Metrics come from the saved
validation/result files; photographs keep their original attribution.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'assets/workcells/strawberry-specimen'
OUT = ROOT / BASE
validation = json.loads((OUT / 'validation.json').read_text())

def p(path):
    return f'{BASE}/{path}'

def source(id, feature, title, publisher, url, image, observation, application, boundary, credit=None, model=None):
    return dict(id=id, feature=feature, title=title, publisher=publisher, url=url,
                image_path=p('reference/'+image), observation=observation,
                application=application, boundary=boundary, credit=credit or publisher,
                **({'model_path':p(model)} if model else {}))

leaves = 'https://strawberrycenterblog.com/2025/12/15/strawberry-anatomy-part-3-leaves-and-stems/'
crowns = 'https://strawberrycenterblog.com/2026/02/19/__trashed/'
fruit = 'https://strawberrycenterblog.com/2025/11/25/strawberry-anatomy-part-2-the-fruit/'
flowers = 'https://strawberrycenterblog.com/2025/11/04/strawberry-anatomy-part-1-the-flower/'
sources = [
    source('crown','Crown & roots','The compressed stem at the plant base','Cal Poly Strawberry Center',crowns,'crown-roots.png',
           'The crown connects leaf bases and roots in a compact, irregular structure. It is not a smooth exposed bulb.',
           'Replaced the large ellipsoid with a smaller irregular crown at the substrate line. Added overlapping basal sheaths and distributed stalk origins.',
           'This exposed bare-root specimen clarifies anatomy; it does not establish the visible shape or dimensions of our growing plant. Root mechanics are omitted.',
           'Photograph: Gerald Holmes, Cal Poly Strawberry Center. Local study copy; redistribution rights not assumed.', 'rest/crown-close.png'),
    source('leaves','Leaves','Leaflets, serrations and short connecting stalks','Cal Poly Strawberry Center',leaves,'leaf-anatomy.jpg',
           'A strawberry leaf has three broad, serrated leaflets with short petiolules. Their outline and central crease matter at tool scale.',
           'The mesh generator consumes a manually estimated width profile from the reference. Bending leaflets use the same wedge surfaces for visual and collision geometry.',
           'The outline is reference-informed, not a calibrated 3D scan. Four hinges per leaflet approximate bending; vein details are visual only.'),
    source('truss','Fruit stalks','Peduncle and branching pedicels','Cal Poly Strawberry Center',leaves,'truss-anatomy.jpg',
           'Fruit attach to branching stalks; they do not each originate independently at a central hub.',
           'Constructed a branching peduncle/pedicel graph. Fruit attach at branch ends, and gravity plus trough contact determine the settled pose.',
           'Hidden connections and depth remain inferred. Stiffness and damping have not been measured on a real stalk.'),
    source('crop','Growing environment','Tabletop strawberry crop structure','Ohio State Kubota Lab','https://u.osu.edu/indoorberry/structures/','tabletop.jpg',
           'The crop has uneven foliage, mixed fruit maturity and hanging trusses supported by the trough edge.',
           'Recorded visible image landmarks, separated uncertain connections, and built one representative specimen before generating a whole crop.',
           'A row photograph cannot prove that every visible stalk belongs to one crown. Camera and depth are approximate; this is not exact reconstruction.',
           'Ohio State Kubota Lab page; tabletop photograph credited in-image to Meteor Systems.'),
    source('section','Crown section','Crown anatomy in section','UC IPM / Cal Poly Strawberry Center',crowns,'crown-section.jpg',
           'Internal crown anatomy belongs to a compressed stem with leaf-base attachments, rather than a swollen root bulb.',
           'Used the section to constrain the external crown interpretation. Kept the crown compact and partially at the substrate surface.',
           'This is anatomical reference. Internal vascular tissues are not simulated.',
           'Strand 2008 / UC IPM, reproduced by Cal Poly with permission. No redistribution license inferred.', 'rest/crown-close.png'),
    source('calyx','Calyx & fruit','Variation at the fruit attachment','Cal Poly Strawberry Center',fruit,'calyx.jpg',
           'Calyx shape and size vary around the fruit attachment. A single repeated star-shaped cap does not capture that variation.',
           'Retained the source as a constraint for the next morphology pass. Current calyx detail remains a visual approximation.',
           'Calyx contact, fruit bruising and detachment are not implemented. This reference has not yet been fully transferred to geometry.'),
    source('surface','Fruit surface','Achenes and the fruit surface','Cal Poly Strawberry Center',fruit,'fruit-surface.jpg',
           'Surface features are embedded in the fruit form and include achene and pistil-remnant detail.',
           'Recorded the evidence for future surface and maturity-specific geometry work; existing fruit remain rigid bodies.',
           'Visible seed details do not establish a contact-accurate surface or a validated bruising model.'),
    source('flowers','Flowers','Open flower anatomy','Cal Poly Strawberry Center',flowers,'flower.jpg',
           'Flowers are a separate developmental stage with petal, sepal and central reproductive structures.',
           'Added a reference for future maturity variation. The current contact specimen does not include simulated flowers.',
           'Source retained for planning; no flower geometry or mechanics are claimed.'),
]

revisions = [
    dict(id='structure',title='Build the structure before multiplying plants',disposition='kept',
         observation='Repeated procedural foliage and centrally arranged stalks were not convincing as one connected plant.',
         decision='Use a visible landmark graph and botanical topology, while recording hidden connections as assumptions.',
         change='Built a single crown with five trifoliate leaves and an independently branching fruit truss. Leaf meshes use the stored reference width profile.',
         evidence='The current specimen has inspectable connections and shared visual/collision leaf surfaces. Its depth and metric dimensions still need measurement.',
         source_ids=['crop','leaves','truss'],before_path=p('checkpoints/v1/rest/three-quarter.png'),after_path=p('rest/three-quarter.png'),artifact_path='tasks/strawberry_specimen/reference-graph.json'),
    dict(id='overlap',title='Reject the overlapping probe initialization',disposition='rejected',
         observation='An early neighboring-fruit probe began inside geometry, producing an approximately 8.9 mm penetration.',
         decision='Reject that diagnostic rather than interpret an initialization impulse as plausible plant behavior.',
         change='Selected a collision-aware approach and paired it with an identical no-contact trajectory. Kept the failed checkpoint for inspection.',
         evidence='The current three probe trials start without contact. Matching controls produce zero probe contacts. This validates initialization and contact attribution, not biological accuracy.',
         source_ids=[],artifact_path=p('checkpoints/v1/neighbor/result.json')),
    dict(id='crown',title='Replace the bulb with a compact crown',disposition='kept',
         observation='The plant base looked like a large smooth bulb, with disconnected-looking stalk origins.',
         decision='Use the bare-root and section references to model a compact compressed stem with overlapping bases at the substrate line.',
         change='Reduced and irregularized the crown, distributed stalk origins, and attached basal sheaths to their bending stalk bodies.',
         evidence='The close-up exposes the revised connections. Re-ran all three contacts and their controls on the saved v4 model. The crown is still fixed and roots are omitted.',
         source_ids=['crown','section'],before_path=p('checkpoints/v2/rest/three-quarter.png'),after_path=p('rest/crown-close.png'),artifact_path=p('validation.json')),
    dict(id='contact',title='Keep the contact evidence inspectable',disposition='kept',
         observation='A stable simulation or attractive render alone could hide missed targets, incidental contacts or untested assumptions.',
         decision='Inspect each contact separately and preserve numerical results alongside close-up video and orbitable recorded geometry.',
         change='Recorded leaf brushing, stalk bending and cluster response from the settled plant, with matched collision-disabled controls.',
         evidence='All intended targets were touched, controls had zero probe contacts, and no physics warnings were recorded. Transient settling penetrations exceeded 1 mm; material calibration remains outstanding.',
         source_ids=[],after_path=p('leaf/contact-1.2.png'),artifact_path=p('validation.json')),
]

questions = {
    'leaf': ('Leaf brushing','Does a tool touch and bend the leaf where it appears to?',
             'A force-limited scripted probe crosses a selected leaflet. The paired control uses the same start state and trajectory with probe collision disabled.',
             'The intended leaf surface was touched. Its neighboring strips also registered contact, consistent with a finite-size probe.',
             'This tests collision placement and response. Leaf stiffness, damping and failure behavior are uncalibrated.'),
    'stalk': ('Stalk bending','Does stalk contact transmit motion through the connected plant?',
              'A force-limited scripted probe pushes the selected peduncle after ten seconds of settling. The matched no-contact control retains the same probe trajectory.',
              'The intended stalk segment was touched. The result file preserves incidental probe contacts and the response of the connected truss.',
              'Capsule chains approximate elasticity. The observed motion is not a measured match to a living stalk.'),
    'neighbor': ('Neighboring fruit','Does pushing one berry affect the surrounding cluster?',
                 'A collision-aware scripted probe approaches a selected berry. Fruit can transmit contact through the cluster and stalk network.',
                 'The intended berry was touched without initial probe overlap. Neighboring fruit already touch at rest, so this is a cluster-response trial.',
                 'This does not test first-contact onset, fruit deformation, bruising or detachment. Fruit are rigid bodies.'),
}
experiments = []
for kind, (title, question, method, finding, limitation) in questions.items():
    result = json.loads((OUT / kind / 'result.json').read_text())
    control = json.loads((OUT / (kind+'-control') / 'result.json').read_text())
    metrics = validation['contact_trials'][kind]
    passed = result['valid_run'] and result['target_touched'] and not result['initial_probe_contacts'] and not control['probe_contacts']
    experiments.append(dict(id=kind,title=title,question=question,method=method,
                            outcome='passed-diagnostic' if passed else 'failed',
                            path=p(kind+'/demo.mp4'),replay_path=p(kind+'/replay.json'),poster_path=p(kind+'/contact-1.2.png'),
                            result_path=p(kind+'/result.json'),control_path=p(kind+'-control/result.json'),
                            metrics=[dict(label='Peak probe-contact force',value=f"{metrics['peak_probe_contact_force_n']:.3f} N"),
                                     dict(label='Maximum probe penetration',value=f"{metrics['max_probe_penetration_mm']:.3f} mm"),
                                     dict(label='Probe contacts in control',value=str(len(control['probe_contacts'])))],
                            finding=finding,limitation=limitation))

study = dict(schema_version=1,title='From real plant to responsive simulation',provenance='recorded',
             status='Contact diagnostics complete · calibration outstanding',
             scope='One reference-informed specimen. Scripted probe tests in MuJoCo; no learned harvesting policy or real-plant validation.',
             objective='Trace the evidence behind the plant: what Astra observed, what changed in the model, and how each physical interaction was checked.',
             preview_path=p('rest/three-quarter.png'),
             checkpoint=dict(label=validation['checkpoint'],sha256=validation['model_sha256'],report_path=p('validation.json')),
             sources=sources,revisions=revisions,experiments=experiments,
             assumptions=[
                 dict(subject='Plant connectivity',basis='observed',value='Trifoliate leaves, a compact crown, and branching fruit stalks are supported by the anatomical references.',consequence='The specimen follows that topology; hidden connections in the crop photograph are still inferred.'),
                 dict(subject='Hidden depth and metric scale',basis='inferred',value='Image landmarks constrain visible placement. All depth coordinates and plant dimensions are reconstructed by judgment.',consequence='We cannot claim an exact digital twin or use this geometry as measured crop clearance.'),
                 dict(subject='Tissue stiffness and damping',basis='assumed',value='Elastic stalk chains and hinged leaflets use selected stiffness/damping values, not real force–deflection measurements.',consequence='Contact is simulated, but force and recovery predictions need physical calibration.'),
                 dict(subject='Crown and substrate boundary',basis='assumed',value='The crown is fixed at the substrate. Roots and root/substrate mechanics are omitted.',consequence='Whole-plant pullout or crown movement cannot be learned credibly from this specimen.'),
                 dict(subject='Fruit and decorative details',basis='assumed',value='Fruit are rigid. Fine calyx and seed geometry is visual detail; bruising, cutting and detachment are not modeled.',consequence='Passing a cluster contact probe does not validate harvesting or delicate fruit handling.'),
                 dict(subject='Contact checks',basis='measured',value='Simulator logs record target contact, matched controls, initial overlaps, force, penetration and solver warnings.',consequence='These are measurements inside this simulation, not measurements of a real plant.'),
             ],
             next_steps=['Fit a consistent camera and quantify projected landmark errors against the selected specimen references.',
                         'Collect real leaf and stalk force–deflection and recovery measurements before fitting tissue parameters.',
                         'Review transient settling contacts over 1 mm and check timestep/contact sensitivity.',
                         'Improve fruit maturity and calyx geometry, then validate cutting/detachment separately before harvesting training.',
                         'Expand to multiple plants only after a coherent specimen passes visual review and the task-relevant contact checks.'])

def check_paths(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if (key.endswith('_path') or key=='path') and isinstance(item,str):
                if not (ROOT/item).is_file():
                    raise FileNotFoundError(item)
            check_paths(item)
    elif isinstance(value,list):
        for item in value: check_paths(item)

check_paths(study)
target=OUT/'study.json'
temp=target.with_suffix('.tmp')
temp.write_text(json.dumps(study,indent=2)+'\n')
temp.replace(target)
manifest_path=ROOT/'assets/workcells/strawberry-harvest/demo.json'
if manifest_path.exists():
    manifest=json.loads(manifest_path.read_text())
    manifest['environment_study_path']=p('study.json')
    manifest['default_view']='research'
    temp=manifest_path.with_suffix('.tmp')
    temp.write_text(json.dumps(manifest,indent=2)+'\n')
    temp.replace(manifest_path)
print(f'Published {len(sources)} sources, {len(revisions)} recorded decisions and {len(experiments)} contact diagnostics.')
