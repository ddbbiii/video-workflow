"""Targeted approved-budget repairs, preserving valid episode artwork."""
import sys
from generate import DEST, submit, write_frame

def evan_overlap():
    p=submit('S32-optical-repair',
       'Edit this existing illustrated image. Preserve the real Evan at LEFT, still gripping his pen, navy coat, brick red scarf, and all room architecture. '
       'DELETE the second Evan currently standing at the far-right WINDOW; make that entire far-right window empty ocean. '
       'Instead show exactly one small likeness of Evan INSIDE THE CENTRAL OVAL GLASS OF THE BRASS FRESNEL LENS, between the dark brass vertical ribs, with his empty hands lowered. '
       'The optical image must be refracted and partly occluded by concentric GLASS ridges. Its entire head and torso stay inside the oval lens boundary. '
       'No actual person anywhere to the right of the pedestal. No frame, mirror, doorway or portal. '
       'Remove the distant lighthouse from the exterior view: windows show open water and distant sky only. '
       'Output one complete widescreen drawing, no labels. Two depictions of Evan total: the real keeper left, and the smaller optical likeness strictly inside the brass lens.',
       'dkl-b',DEST/'final/S32.png',cel=True)
    write_frame(p,'S32')

def andrew_overlap():
    p=submit('S22-optical-repair',
       'Edit this existing illustrated image. Preserve Andrew at LEFT holding his enamel cup and all lighthouse room architecture. '
       'Show exactly one small likeness of Evan INSIDE THE CENTRAL OVAL GLASS OF THE BRASS FRESNEL LENS, partly refracted and occluded by its concentric glass ridges. '
       'The likeness has one hand raised in a different action from Andrew; keep the entire head and torso inside the lens boundary. '
       'Keep every sea window empty of people and show only open ocean. No mirror, frame, portal, or person outside the lens. Preserve the cold cel-shaded graphic-novel style.',
       'dkl-b',DEST/'final/S22.png',cel=True)
    write_frame(p,'S22')

def three_inside():
    p=submit('S46-optical-repair',
       'Edit this existing illustrated image. Preserve the real Evan seated at LEFT writing, his clothing, desk, and lighthouse architecture. '
       'DELETE the three men currently standing in the far-right window; replace them with empty open ocean. '
       'Show exactly three small, recognizable likenesses of the missing keepers INSIDE THE CENTRAL OVAL GLASS OF THE BRASS FRESNEL LENS, between its dark brass ribs. '
       'The three heads and upper torsos must fit entirely within the glass oval, partly refracted and occluded by concentric glass ridges. '
       'No figures elsewhere except the real Evan at the desk. No mirror, portal, or extra person. Preserve the cold cel-shaded graphic-novel style.',
       'dkl-b',DEST/'final/S46.png',cel=True)
    write_frame(p,'S46')

def iain_inside():
    p=submit('S47-optical-repair',
       'Edit this existing illustrated image. Preserve the real Evan seated at LEFT with pen and all room architecture. '
       'Inside the central oval glass of the brass Fresnel lens, show one small likeness of Iain, identifiable by black hair, slate waistcoat and white shirt. '
       'His raised fingertips touch the INNER side of the glass in a distinct knocking pose. Keep his whole head and hand inside the oval lens boundary, refracted and partly occluded by concentric glass ridges. '
       'All sea windows outside the lens remain empty open ocean. No actual person elsewhere, no mirror, frame or portal. Preserve the cold cel-shaded graphic-novel style.',
       'dkl-b',DEST/'final/S47.png',cel=True)
    write_frame(p,'S47')

if __name__=='__main__':
    {'S22':andrew_overlap,'S32':evan_overlap,'S46':three_inside,'S47':iain_inside}[sys.argv[1]]()
