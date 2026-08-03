class GarmentCalculator:
    """Calculates fabric estimations and fit suggestions based on body dimensions."""

    @staticmethod
    def estimate_fabric_meters(garment_type: str, length_inches: float, chest_inches: float) -> dict:
        """Estimates required fabric length in meters (standard 54-inch width cloth)."""
        garment_clean = garment_type.lower()
        base_meters = 2.25

        if "shalwar kameez" in garment_clean or "suit" in garment_clean:
            # Formula: (Length * 2 + Sleeve Length + hem margins) converted to meters
            estimated_inches = (length_inches * 2.1) + 24.0
            if chest_inches > 44.0:
                estimated_inches += 12.0  # Additional width allowance for larger chest sizes
            base_meters = round(estimated_inches / 39.37, 2)

        elif "shirt" in garment_clean:
            estimated_inches = length_inches + 30.0
            base_meters = round(estimated_inches / 39.37, 2)

        elif "trouser" in garment_clean or "pant" in garment_clean:
            estimated_inches = length_inches + 8.0
            base_meters = round(estimated_inches / 39.37, 2)

        elif "waistcoat" in garment_clean or "vest" in garment_clean:
            base_meters = 1.25

        return {
            "garment_type": garment_type,
            "recommended_meters": max(base_meters, 1.0),
            "fabric_width_standard": "54 inches",
            "notes": "Includes standard pockets, collar allowances, and cuff margins."
        }