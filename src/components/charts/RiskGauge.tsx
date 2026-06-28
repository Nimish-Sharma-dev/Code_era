import { StyleSheet, Text, View } from 'react-native';
import Svg, { Defs, LinearGradient, Path, Stop } from 'react-native-svg';

import { Colors } from '@/constants/theme';

interface RiskGaugeProps {
  score: number; // 0-100
  band: 'LOW' | 'MEDIUM' | 'HIGH';
}

const ARC_LENGTH = 125.66; // PI * r(40) for the semicircle path below

export function RiskGauge({ score, band }: RiskGaugeProps) {
  const percentage = Math.max(0, Math.min(score, 100)) / 100;
  const dashOffset = ARC_LENGTH * (1 - percentage);
  const bandColor =
    band === 'HIGH' ? Colors.loss : band === 'MEDIUM' ? Colors.warning : Colors.gain;

  return (
    <View style={styles.wrap}>
      <Svg width={256} height={128} viewBox="0 0 100 50">
        <Defs>
          <LinearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <Stop offset="0%" stopColor={Colors.gain} />
            <Stop offset="50%" stopColor={Colors.warning} />
            <Stop offset="100%" stopColor={Colors.loss} />
          </LinearGradient>
        </Defs>
        <Path
          d="M 10 50 A 40 40 0 0 1 90 50"
          stroke="#2A2D3A"
          strokeWidth={8}
          strokeLinecap="round"
          fill="none"
        />
        <Path
          d="M 10 50 A 40 40 0 0 1 90 50"
          stroke="url(#gaugeGradient)"
          strokeWidth={8}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={`${ARC_LENGTH} ${ARC_LENGTH}`}
          strokeDashoffset={dashOffset}
        />
      </Svg>
      <View style={styles.labelOverlay} pointerEvents="none">
        <Text style={styles.score}>{score}</Text>
        <Text style={[styles.band, { color: bandColor }]}>{band} RISK</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: 256,
    height: 128,
    alignItems: 'center',
  },
  labelOverlay: {
    position: 'absolute',
    bottom: 4,
    alignItems: 'center',
  },
  score: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 32,
    color: Colors.onSurface,
  },
  band: {
    fontFamily: 'Inter_700Bold',
    fontSize: 14,
    letterSpacing: 1.5,
  },
});
