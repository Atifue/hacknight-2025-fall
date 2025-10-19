#!/usr/bin/env python3
"""
Speech Therapy Tips Generator
Provides personalized advice based on detected stutters
"""

import json
import os
from typing import Dict, List

class SpeechTherapyAdvisor:
    """Generate therapy tips based on stutter types"""
    
    def __init__(self):
        # Phoneme-specific articulation guidance
        self.sound_guidance = {
            's': {
                'position': "Tongue tip barely touches the ridge behind your top teeth. Create a narrow channel for air.",
                'common_issue': "Pressing tongue too hard or too far forward.",
                'fix': "Lighten the contact. Think 'feather touch' not 'seal'. Keep airflow steady and gentle.",
                'practice': "Whisper 's' first (less tension), then gradually add voice: 's' → 'sa' → 'see' → 'slide'."
            },
            't': {
                'position': "Tongue tip touches the alveolar ridge (bump behind top teeth), then releases.",
                'common_issue': "Pressing too hard or holding the contact too long.",
                'fix': "Touch lightly and release immediately. It's a quick 'tap', not a 'hold'.",
                'practice': "Practice light taps: 't' by itself 10 times, focusing on quick release. Then: 'ta', 'to', 'too'."
            },
            'd': {
                'position': "Same as 't' but voiced. Tongue tip touches alveolar ridge lightly.",
                'common_issue': "Too much pressure or blocking airflow completely.",
                'fix': "Keep it light and quick. Let your voice start immediately.",
                'practice': "'d' alone, then 'da', 'do', 'did'. Feel the vibration in your throat."
            },
            'k': {
                'position': "Back of tongue touches soft palate (back of roof of mouth), then releases.",
                'common_issue': "Jamming the back of tongue up too hard.",
                'fix': "Gentle contact, quick release. Don't build up pressure behind the tongue.",
                'practice': "Say 'k' alone softly. Feel where your tongue touches. Then: 'ka', 'key', 'can'."
            },
            'g': {
                'position': "Same position as 'k' but voiced.",
                'common_issue': "Locking the back of tongue and building tension.",
                'fix': "Light touch, let voice flow through. Don't hold the position.",
                'practice': "'g' with voice, then 'go', 'get', 'good'. Feel throat vibration."
            },
            'p': {
                'position': "Lips close lightly, then release with a small burst of air.",
                'common_issue': "Pressing lips together too hard.",
                'fix': "Barely close lips. Let them 'pop' open naturally with air pressure.",
                'practice': "'p' softly (like a tiny bubble popping), then 'pa', 'po', 'pop'."
            },
            'b': {
                'position': "Same as 'p' but voiced.",
                'common_issue': "Clamping lips together.",
                'fix': "Soft contact, immediate release with voice.",
                'practice': "'b' alone (feel lips vibrate), then 'ba', 'be', 'bee'."
            },
            'f': {
                'position': "Top teeth rest lightly on bottom lip, air flows through.",
                'common_issue': "Biting the lip too hard.",
                'fix': "Teeth barely touch lip. Focus on gentle, continuous airflow.",
                'practice': "Sustain 'fffffff' for 5 seconds with minimal pressure. Then: 'fa', 'far', 'fun'."
            },
            'v': {
                'position': "Same as 'f' but voiced.",
                'common_issue': "Too much lip tension.",
                'fix': "Light contact, let voice flow continuously.",
                'practice': "'vvvvv' sustained, feel vibration. Then: 'va', 'very', 'van'."
            },
            'w': {
                'position': "Round lips, then release while voicing.",
                'common_issue': "Holding the rounded position too long.",
                'fix': "Quick lip movement from round to open. Don't freeze in the 'w' position.",
                'practice': "'w' quickly, then 'wa', 'we', 'want'. Keep it fluid and moving."
            },
            'm': {
                'position': "Lips close, air flows through nose, voice resonates.",
                'common_issue': "Pressing lips too tight, blocking nasal airflow.",
                'fix': "Soft lip closure, feel vibration in nose and lips.",
                'practice': "Hum 'mmmmm', feel the buzz. Then: 'ma', 'me', 'mom'."
            },
            'n': {
                'position': "Tongue tip touches alveolar ridge, air flows through nose.",
                'common_issue': "Blocking nasal passage or pressing tongue too hard.",
                'fix': "Light tongue contact, open nasal passage. Feel nose vibration.",
                'practice': "'nnnnn' sustained (feel nose vibrate), then 'na', 'no', 'nice'."
            },
            'l': {
                'position': "Tongue tip touches alveolar ridge, air flows around sides of tongue.",
                'common_issue': "Pressing tongue flat against roof of mouth.",
                'fix': "Tip touches, but sides of tongue stay down. Air flows around.",
                'practice': "'llll' sustained, then 'la', 'lo', 'let'. Keep sides relaxed."
            },
            'r': {
                'position': "Tongue bunches slightly back (or tip curls slightly up), without touching roof.",
                'common_issue': "Tongue too tense or touching too much.",
                'fix': "Keep tongue loose and floating. Voice should flow freely.",
                'practice': "Growl 'rrrr' gently, then 'ra', 're', 'really'. Stay relaxed."
            },
            'sh': {
                'position': "Tongue near roof of mouth (not touching), lips slightly rounded, air flows through center.",
                'common_issue': "Tongue pressed against roof or too much air pressure.",
                'fix': "Create space for air to flow. Soft, gentle stream.",
                'practice': "'shhhhh' like calming a baby (gentle!), then 'sha', 'she', 'show'."
            },
            'ch': {
                'position': "Similar to 'sh' but with a quick stop at the start (like 't' + 'sh').",
                'common_issue': "Holding the stop too long before the 'sh' part.",
                'fix': "Quick release from the 't' into flowing 'sh'. One smooth motion.",
                'practice': "'ch' alone, then 'cha', 'cho', 'chew'. Make it fluid."
            },
            'j': {
                'position': "Like 'ch' but voiced (similar to 'd' + 'zh').",
                'common_issue': "Separating the sounds instead of blending.",
                'fix': "Quick release with immediate voicing. One sound, not two.",
                'practice': "'j' (like 'dge'), then 'ja', 'jo', 'jump'. Keep voice going throughout."
            },
            'vowel': {
                'position': "Open vocal tract, relaxed jaw, voice flows freely.",
                'common_issue': "Tension in jaw or throat.",
                'fix': "Drop jaw naturally. Don't force. Voice should feel easy.",
                'practice': "Yawn, then say vowels: 'ah', 'ay', 'ee', 'oh', 'oo'. Keep that open feeling."
            }
        }
        # Tips database organized by stutter type
        self.tips = {
            "repetition": {
                "description": "Repetitions (like 'b-b-b-ball') occur when your speech mechanism restarts the same sound instead of flowing through smoothly.",
                "why_it_happens": "Excess tension in articulators, rushed timing, or disrupted breath-speech coordination.",
                "techniques": [
                    "**Prolonged Speech (Stretching)**: Extend the first sound smoothly instead of repeating it. Instead of 'b-b-b-ball', do 'baaaaaall' (stretch 2-3 seconds). Stretching prevents the repetition pattern—your brain can't send the 'restart' signal when you're already producing continuous sound.",
                    "**Light Articulatory Contact**: Use minimal pressure when lips/tongue form sounds. Touch lips together gently for B/P/M (like touching a soap bubble). Tongue barely contacts roof of mouth for T/D/K. Heavy pressure causes articulators to 'stick' and trigger repetitions.",
                    "**Continuous Phonation**: Keep airflow and voicing continuous between sounds—never stop and restart. Start by humming between words: 'I (hmmm) like (hmmm) dogs', then gradually reduce the hum but maintain continuous airflow.",
                ],
                "exercises": [
                    "**Stretching Practice**: Start with isolated sounds (mmmm, sssss), then syllables (maaaa, seee), then full words (more, sun, ball). Hold each sound 2-3 seconds.",
                    "**Light Contact Drill**: Say 'paper, baby, maybe' with feather-light lip contact. Use a mirror to check you're not clenching.",
                    "**Continuous Flow**: Read sentences while maintaining steady breath support. Think of your voice as a river that never stops flowing."
                ],
                "mouth_positions": [
                    "For 't' sounds: Tongue tip barely touches ridge behind top teeth, no pressure.",
                    "For 'k' sounds: Back of tongue lightly touches soft palate, quick release.",
                    "For 'p/b' sounds: Close lips like touching a soap bubble—soft, not clenched."
                ]
            },
            
            "acoustic_repetition": {
                "description": "Rapid sound repetitions (like 't-t-t-t') that may not be captured in transcription.",
                "why_it_happens": "Excess tension in articulators, rushed timing, or disrupted breath-speech coordination (same as repetitions).",
                "techniques": [
                    "**Prolonged Speech (Stretching)**: Extend the first sound smoothly instead of repeating it. Stretch it 2-3 seconds. This prevents the repetition pattern—your brain can't restart when you're producing continuous sound.",
                    "**Light Articulatory Contact**: Use minimal pressure. Touch lips together gently for B/P/M (soap bubble touch). Tongue barely contacts roof for T/D/K. Heavy pressure causes 'sticking' and triggers repetitions.",
                    "**Continuous Phonation**: Keep airflow and voicing continuous—never stop and restart. Hum between words initially, then maintain the continuous airflow feeling.",
                ],
                "exercises": [
                    "**Stretching Practice**: Isolated sounds (mmmm, sssss) → syllables (maaaa, seee) → full words. Hold 2-3 seconds each.",
                    "**Light Contact Drill**: Say words with feather-light contact. Use a mirror to check tension.",
                    "**Continuous Flow**: Read maintaining steady breath. Voice like a river that never stops."
                ],
                "mouth_positions": [
                    "Position articulators before attempting the sound.",
                    "Check tension in mirror—jaw, lips, tongue should be relaxed.",
                    "Practice while exhaling steadily—never hold breath."
                ]
            },
            
            "prolongation": {
                "description": "Prolongations (like 'sssssnake') occur when a sound is held longer than intended, usually due to excessive tension or air pressure.",
                "why_it_happens": "Too much articulatory pressure, excessive airflow, or inability to transition to the next sound.",
                "techniques": [
                    "**Gentle Onset**: Start sounds softly and gradually increase to normal volume. Begin at 20% volume and fade up: '^s^s^sun' → 'sun'. Like turning up a volume dial, not flipping a switch. Hard onsets create tension that leads to prolongations.",
                    "**Reduced Air Pressure**: Use less forceful airflow, especially on S, F, SH, TH. Hold hand in front of mouth—feel gentle airflow, not a blast. Think 'blowing on hot soup' not 'blowing out candles'. Excessive air pressure builds up and creates prolongations.",
                    "**Quick Transition Drill**: Practice moving rapidly from the prolonged sound to the next sound. If stuck on 'ssssnake,' practice: 's-nake' (quick s, immediate transition). Don't allow time to hold the sound. The faster you transition, the less opportunity for prolongation.",
                ],
                "exercises": [
                    "**Gentle Start Practice**: Start with vowels (easier), then fricatives like S/F/SH. Begin each word as a whisper, then gradually add voice.",
                    "**Reduced Air Drill**: Say 'sun, fun, shoe' with minimal air. If you hear loud hissing, you're using too much air. Hold hand in front—should feel gentle breeze.",
                    "**Quick Transition with Metronome**: Practice consonant-vowel pairs at increasing speeds: 'sa, se, si, so, su'. Make the consonant as brief as possible. Use metronome to speed up gradually."
                ],
                "mouth_positions": [
                    "For 's' sounds: Tongue tip barely touches ridge behind top teeth. Create narrow channel, not a seal.",
                    "For 'f' sounds: Top teeth rest lightly on bottom lip—don't bite down hard.",
                    "For 'sh' sounds: Tongue near roof but NOT touching—keep space for gentle airflow.",
                    "Keep jaw loose—tension in jaw travels to tongue and lips."
                ]
            },
            
            "block": {
                "description": "Blocks are complete stoppages of airflow/voicing—you physically cannot produce sound despite trying, often with visible tension.",
                "why_it_happens": "Extreme tension in multiple muscle groups (jaw, tongue, throat, chest), often accompanied by breath-holding.",
                "techniques": [
                    "**Pre-Phonatory Airflow**: Establish airflow BEFORE attempting the word. (1) Breathe in through nose (3 counts), (2) Begin gentle exhalation, (3) While air is flowing, add voicing: start with 'h' sound, then target word. Example: 'h-ball' or hum first 'mmm-ball'. Blocks occur when you try to speak on held breath or with closed vocal tract.",
                    "**Voluntary Relaxation (Cancellation)**: When you feel a block starting, STOP immediately. Don't fight it. (1) Pause completely, (2) Release all tension (drop shoulders, unclench jaw), (3) Take one breath, (4) Position mouth with LIGHT contact, (5) Begin again with gentle airflow. Fighting a block increases tension and makes it worse.",
                    "**Progressive Muscle Relaxation**: Systematically relax speech muscle groups. (1) Clench jaw 5 seconds, then release completely, (2) Press tongue hard against roof, then let it float, (3) Tense neck/shoulders, then let them drop. Regular practice reduces baseline tension and makes blocks less likely.",
                ],
                "exercises": [
                    "**Pre-Airflow Practice**: Before any difficult word, ensure you're exhaling first. Practice: breathe in → start exhaling → add 'h' sound → say word. Never try to speak while holding breath.",
                    "**Cancellation Training**: Intentionally create a mild block, then practice the cancellation sequence. Train your brain that pausing is OK. Stop, release tension, breathe, restart gently.",
                    "**Daily Relaxation**: Do this sequence before speaking situations: Clench jaw (5s) → release. Press tongue up (5s) → release. Tense shoulders (5s) → release. Check for tension during speech—if you notice jaw/tongue/throat tightness, pause and release."
                ],
                "mouth_positions": [
                    "Don't 'lock' articulators—keep them mobile and loose.",
                    "For blocks on 'k/g': Back of tongue should lightly touch palate, not jam against it.",
                    "For blocks on 'p/b/m': Keep lips soft, not squeezed together.",
                    "Jaw should be loose, not clenched—check by wiggling it gently."
                ],
                "emergency_tips": [
                    "If blocked RIGHT NOW: STOP. Take a breath. Release all tension. Start over slowly.",
                    "Use pre-airflow: Start with 'h' or 'mmm' to get air moving before the word.",
                    "Change the word: If really stuck, use a synonym instead of forcing it.",
                    "Pausing is OK: A calm silence is better than visible struggle."
                ]
            }
        }
        
        # General tips that apply to all stutter types
        self.general_tips = [
            "**Stay Hydrated**: Dry mouth increases tension. Drink water before speaking.",
            "**Sleep Well**: Fatigue makes stuttering worse. Get 7-9 hours of sleep.",
            "**Reduce Stress**: Stress increases stuttering. Practice mindfulness, meditation, or deep breathing.",
            "**Accept Stuttering**: Fighting stuttering makes it worse. Accept that it may happen.",
            "**Eye Contact**: Maintain natural eye contact even during stutters - it builds confidence.",
            "**Don't Apologize**: Stuttering isn't something to apologize for.",
            "**Speak at Comfortable Pace**: You don't need to rush. Slower speech is clearer speech.",
            "**Join Support Groups**: Connect with others who stutter. You're not alone."
        ]
    
    def generate_advice(self, detection_results: Dict) -> Dict:
        """
        Generate personalized advice based on detection results
        
        Args:
            detection_results: Output from stutter_detector.detect_all()
                Should have 'events' list with detected stutters
        
        Returns:
            Dict with personalized advice, tips, and exercises
        """
        events = detection_results.get('events', [])
        words = detection_results.get('words', [])
        
        if not events:
            return {
                "summary": "No stutters detected! Great job!",
                "encouragement": "Your speech was fluent. Keep up the good work!",
                "preventive_tips": self.general_tips[:4]
            }
        
        # Analyze what types of stutters occurred
        stutter_counts = {}
        specific_words = []
        
        for event in events:
            stype = event['type']
            stutter_counts[stype] = stutter_counts.get(stype, 0) + 1
            
            # For acoustic repetitions, use the target word and inferred sound
            if stype == 'acoustic_repetition' and 'target_word' in event and 'inferred_sound' in event:
                specific_words.append({
                    'word': event['target_word'],  # The actual word they were trying to say
                    'inferred_sound': event['inferred_sound'],  # The sound that was repeated
                    'type': stype,
                    'time': f"{event['start']:.1f}s",
                    'event': event  # Keep full event for guidance generation
                })
            elif 'word' in event:
                specific_words.append({
                    'word': event['word'],
                    'type': stype,
                    'time': f"{event['start']:.1f}s",
                    'event': event
                })
        
        # Generate personalized advice
        advice = {
            "summary": self._generate_summary(stutter_counts, len(words)),
            "detected_patterns": self._format_patterns(stutter_counts),
            "specific_moments": specific_words[:5],  # Top 5 specific instances
            "word_specific_guidance": [],  # NEW: Specific guidance for each stuttered word
            "techniques_to_practice": [],
            "exercises": [],
            "general_tips": self.general_tips[:5],
            "encouragement": self._generate_encouragement(stutter_counts, len(events))
        }
        
        # Add word-specific guidance for each stuttered word
        for moment in specific_words[:3]:  # Top 3 words
            if moment['word']:
                # For acoustic repetitions, pass the inferred sound
                if moment['type'] == 'acoustic_repetition' and 'inferred_sound' in moment:
                    word_guidance = self.get_word_specific_guidance(
                        moment['word'], 
                        moment['type'],
                        inferred_sound=moment['inferred_sound']
                    )
                else:
                    word_guidance = self.get_word_specific_guidance(moment['word'], moment['type'])
                advice["word_specific_guidance"].append(word_guidance)
        
        # Add specific tips for each stutter type detected
        for stype in stutter_counts.keys():
            if stype in self.tips:
                tips = self.tips[stype]
                advice["techniques_to_practice"].extend([
                    {"stutter_type": stype.replace('_', ' ').title(), 
                     "tip": tip}
                    for tip in tips["techniques"][:3]
                ])
                advice["exercises"].extend([
                    {"stutter_type": stype.replace('_', ' ').title(),
                     "exercise": ex}
                    for ex in tips["exercises"][:2]
                ])
        
        return advice
    
    def _generate_summary(self, stutter_counts: Dict, total_words: int) -> str:
        """Generate a summary of the analysis"""
        total_stutters = sum(stutter_counts.values())
        stutter_rate = (total_stutters / total_words * 100) if total_words > 0 else 0
        
        types_str = ", ".join([
            f"{count} {stype.replace('_', ' ')}" 
            for stype, count in stutter_counts.items()
        ])
        
        severity = "mild" if stutter_rate < 5 else "moderate" if stutter_rate < 10 else "notable"
        
        return (f"Detected {total_stutters} stutter event(s) in {total_words} words "
                f"({stutter_rate:.1f}% stutter rate - {severity}). "
                f"Types: {types_str}.")
    
    def _format_patterns(self, stutter_counts: Dict) -> List[str]:
        """Format stutter patterns for display"""
        patterns = []
        for stype, count in sorted(stutter_counts.items(), key=lambda x: x[1], reverse=True):
            if stype in self.tips:
                tip_info = self.tips[stype]
                pattern_text = f"**{stype.replace('_', ' ').title()}** ({count}x): {tip_info['description']}"
                if 'why_it_happens' in tip_info:
                    pattern_text += f"\n    → Why: {tip_info['why_it_happens']}"
                patterns.append(pattern_text)
        return patterns
    
    def _generate_encouragement(self, stutter_counts: Dict, total_events: int) -> str:
        """Generate encouraging message"""
        if total_events <= 2:
            return "You're doing great! Just a couple of moments of dysfluency - totally normal."
        elif total_events <= 5:
            return "Remember: Everyone has dysfluent moments. You're working on it and that's what matters!"
        else:
            return "Awareness is the first step to improvement. These techniques WILL help with practice. Be patient with yourself!"
    
    def get_detailed_tips_for_type(self, stutter_type: str) -> Dict:
        """Get all detailed tips for a specific stutter type"""
        return self.tips.get(stutter_type, {})
    
    def get_word_specific_guidance(self, word: str, stutter_type: str, inferred_sound: str = None) -> Dict:
        """
        Generate specific guidance for a particular word that was stuttered
        
        Args:
            word: The word that was stuttered on (e.g., "slide")
            stutter_type: Type of stutter (repetition, prolongation, block, acoustic_repetition)
            inferred_sound: For acoustic repetitions, the specific sound that was repeated (e.g., 't', 'th')
        
        Returns:
            Dict with word-specific tips
        """
        word_clean = word.lower().strip('.,!?;:\'"')
        
        # Identify the problematic sound
        if stutter_type == 'acoustic_repetition' and inferred_sound:
            # Use the inferred sound from acoustic analysis
            problem_sound = inferred_sound
        elif stutter_type in ['prolongation', 'acoustic_repetition']:
            # Usually the first sound is the issue
            problem_sound = word_clean[0] if word_clean else ''
        elif stutter_type == 'repetition':
            # Could be any sound in a repetition
            problem_sound = word_clean[0] if word_clean else ''
        else:  # block
            # Often the first sound
            problem_sound = word_clean[0] if word_clean else ''
        
        # Get specific guidance for that sound
        sound_info = self.sound_guidance.get(problem_sound, self.sound_guidance.get('vowel'))
        
        # Build word-specific advice
        guidance = {
            'word': word,
            'problem_sound': problem_sound.upper(),
            'stutter_type': stutter_type.replace('_', ' ').title(),
            'how_to_say_it': self._generate_word_guide(word_clean, problem_sound, stutter_type),
            'sound_details': sound_info,
            'practice_sequence': self._generate_practice_sequence(word_clean, problem_sound)
        }
        
        return guidance
    
    def _generate_word_guide(self, word: str, problem_sound: str, stutter_type: str) -> str:
        """Generate step-by-step guide for saying a specific word"""
        guides = []
        
        if stutter_type == 'prolongation':
            guides.append(f"1. **Position**: Set your mouth for '{problem_sound}' sound BEFORE you start.")
            guides.append(f"2. **Light Contact**: Touch lightly - don't press hard or tense up.")
            guides.append(f"3. **Gentle Start**: Begin the sound softly, like turning up volume gradually.")
            guides.append(f"4. **Flow Through**: Smoothly transition from '{problem_sound}' to the rest of '{word}'.")
            guides.append(f"5. **Say Together**: Think of '{word}' as ONE sound, not separate parts.")
        
        elif stutter_type in ['repetition', 'acoustic_repetition']:
            guides.append(f"1. **Breathe First**: Take a breath BEFORE attempting '{word}'.")
            guides.append(f"2. **Easy Onset**: Start '{problem_sound}' gently - no forcing.")
            guides.append(f"3. **Continuous**: Keep airflow going - don't stop and restart.")
            guides.append(f"4. **Stretch It**: If you feel a repeat coming, STRETCH the sound instead: '{problem_sound}...{word[1:]}'")
            guides.append(f"5. **Stay Calm**: If you repeat, that's OK. Finish the word smoothly.")
        
        else:  # block
            guides.append(f"1. **Prep Work**: Position your mouth for '{problem_sound}' while breathing.")
            guides.append(f"2. **Release Tension**: Check jaw, neck, face - relax any tightness.")
            guides.append(f"3. **Voluntary Start**: YOU control when to start - don't rush.")
            guides.append(f"4. **Gentle Push**: Use gentle air pressure, not forceful pushing.")
            guides.append(f"5. **Bounce Through**: If blocked, try 'uh-{word}' to get airflow going.")
        
        return "\n   ".join(guides)
    
    def _generate_practice_sequence(self, word: str, problem_sound: str) -> List[str]:
        """Generate a practice sequence building up to the full word"""
        sequence = []
        
        # Level 1: Sound in isolation
        sequence.append(f"**Level 1**: Say '{problem_sound}' by itself 10 times slowly and gently")
        
        # Level 2: Sound + vowel
        if len(word) > 1:
            sequence.append(f"**Level 2**: '{problem_sound}{word[1]}' (first 2 letters)")
        
        # Level 3: First syllable or half
        if len(word) > 3:
            mid = len(word) // 2
            sequence.append(f"**Level 3**: '{word[:mid]}' (first half)")
        
        # Level 4: Full word slow
        sequence.append(f"**Level 4**: '{word}' SLOWLY with exaggerated smoothness")
        
        # Level 5: Full word normal
        sequence.append(f"**Level 5**: '{word}' at normal speed, staying relaxed")
        
        # Level 6: In a sentence
        sequence.append(f"**Level 6**: Use '{word}' in a short sentence")
        
        return sequence


def format_advice_for_display(advice: Dict) -> str:
    """Format advice dictionary as readable text"""
    output = []
    output.append("=" * 70)
    output.append("SPEECH THERAPY ADVICE")
    output.append("=" * 70)
    output.append("")
    
    output.append(f"📊 SUMMARY")
    output.append(advice['summary'])
    output.append("")
    
    if 'detected_patterns' in advice and advice['detected_patterns']:
        output.append("🔍 DETECTED PATTERNS & WHY THEY HAPPEN")
        for pattern in advice['detected_patterns']:
            output.append(f"  • {pattern}")
        output.append("")
    
    if 'specific_moments' in advice and advice['specific_moments']:
        output.append("📍 SPECIFIC MOMENTS")
        for moment in advice['specific_moments']:
            output.append(f"  • {moment['time']}: '{moment['word']}' ({moment['type'].replace('_', ' ')})")
        output.append("")
    
    # NEW: Word-specific guidance section
    if 'word_specific_guidance' in advice and advice['word_specific_guidance']:
        output.append("🎯 WORD-SPECIFIC GUIDANCE")
        output.append("-" * 70)
        for guidance in advice['word_specific_guidance']:
            output.append(f"\n  Word: '{guidance['word']}' | Problem Sound: [{guidance['problem_sound']}] | Type: {guidance['stutter_type']}")
            output.append("")
            
            # How to say it
            output.append(f"  ✓ HOW TO SAY '{guidance['word'].upper()}':")
            output.append("   " + guidance['how_to_say_it'])
            output.append("")
            
            # Sound details
            sound = guidance['sound_details']
            output.append(f"  🗣️  '{guidance['problem_sound']}' SOUND DETAILS:")
            output.append(f"     Position: {sound['position']}")
            output.append(f"     Common Issue: {sound['common_issue']}")
            output.append(f"     Fix: {sound['fix']}")
            output.append(f"     Practice: {sound['practice']}")
            output.append("")
            
            # Practice sequence
            output.append(f"  📈 PRACTICE SEQUENCE FOR '{guidance['word']}':")
            for step in guidance['practice_sequence']:
                output.append(f"     {step}")
            output.append("")
            output.append("   " + "-" * 65)
        output.append("")
    
    if 'techniques_to_practice' in advice and advice['techniques_to_practice']:
        output.append("💡 TECHNIQUES TO PRACTICE")
        for tech in advice['techniques_to_practice']:
            output.append(f"  [{tech['stutter_type']}] {tech['tip']}")
        output.append("")
    
    if 'exercises' in advice and advice['exercises']:
        output.append("🏋️ RECOMMENDED EXERCISES")
        for ex in advice['exercises']:
            output.append(f"  [{ex['stutter_type']}] {ex['exercise']}")
        output.append("")
    
    if 'general_tips' in advice and advice['general_tips']:
        output.append("🌟 GENERAL TIPS")
        for tip in advice['general_tips']:
            output.append(f"  • {tip}")
        output.append("")
    
    output.append("💪 " + advice.get('encouragement', 'Keep practicing!'))
    output.append("")
    output.append("=" * 70)
    
    return "\n".join(output)


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 speech_therapy_tips.py <detection_results.json>")
        print("   or: python3 speech_therapy_tips.py <audio_file>")
        print("\nThis script provides speech therapy advice based on stutter detection results.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Check if it's a JSON file or audio file
    if input_file.endswith('.json'):
        # Load detection results from JSON
        with open(input_file, 'r') as f:
            results = json.load(f)
    else:
        # Run detection first
        from stutter_detector import detect_all
        print(f"Analyzing {input_file}...")
        results = detect_all(input_file, verbose=False)
        print("Analysis complete!\n")
    
    # Generate advice
    advisor = SpeechTherapyAdvisor()
    advice = advisor.generate_advice(results)
    
    # Display formatted advice
    print(format_advice_for_display(advice))
    
    # Optionally save to JSON
    if '--json' in sys.argv:
        # Create outputFiles directory if it doesn't exist
        os.makedirs("outputFiles", exist_ok=True)
        base_name = os.path.basename(input_file).rsplit('.', 1)[0]
        output_file = f"outputFiles/{base_name}_advice.json"
        with open(output_file, 'w') as f:
            json.dump(advice, f, indent=2)
        print(f"\n✅ Advice saved to: {output_file}")

