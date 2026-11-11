import { LocateFixed } from 'lucide-react-native';
import { Platform, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE } from 'react-native-maps';

import { colors, radius } from '@/lib/theme';
import type { NearbyVehicle } from '@/lib/types';

const DEFAULT_REGION = {
  latitude: 25.7617,
  longitude: -80.1918,
  latitudeDelta: 0.055,
  longitudeDelta: 0.055,
};

type MapPanelProps = {
  center?: { latitude: number; longitude: number };
  vehicles?: NearbyVehicle[];
};

export function MapPanel({ center, vehicles = [] }: MapPanelProps) {
  const provider = Platform.OS === 'android' ? PROVIDER_GOOGLE : undefined;
  const providerLabel = Platform.OS === 'ios' ? 'Apple Maps' : 'Google Maps';
  const region = center ? { ...DEFAULT_REGION, ...center } : DEFAULT_REGION;

  return (
    <View accessibilityLabel={`${providerLabel} pickup map`} style={styles.frame}>
      <MapView
        provider={provider}
        region={region}
        showsCompass
        showsMyLocationButton
        showsUserLocation
        style={StyleSheet.absoluteFill}
      >
        <Marker coordinate={region} title="Pickup area" />
        {vehicles.map((vehicle) => (
          <Marker
            coordinate={{ latitude: vehicle.latitude, longitude: vehicle.longitude }}
            key={vehicle.vehicle_id}
            pinColor={colors.emerald}
            title="Available vehicle · approximate location"
          />
        ))}
      </MapView>
      <View style={styles.badge}>
        <LocateFixed color={colors.emerald} size={15} />
        <Text style={styles.badgeText}>{providerLabel}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    height: 220,
    overflow: 'hidden',
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.large,
    backgroundColor: colors.sky,
  },
  badge: {
    position: 'absolute',
    bottom: 12,
    left: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 11,
    paddingVertical: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.white,
  },
  badgeText: { color: colors.forest, fontSize: 11, fontWeight: '800' },
});
