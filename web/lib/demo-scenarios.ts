import { PlannerResult, TestCase } from './types';

interface DemoScenario {
  id: string;
  name: string;
  change: string;
  defect: string;
  result: PlannerResult;
}

const speedTests: TestCase[] = [
  { test_id: 'XRAY-1001', title: 'Digital Cluster: Speedometer CAN Signal Scaling (0x1A4)', domain: 'Digital_Cluster_Speedometer', similarity_score: 0.88, estimated_duration_seconds: 45 },
  { test_id: 'XRAY-1013', title: 'CAN Signal Scaling: Edge Case 0x0000 & 0xFFFF', domain: 'Digital_Cluster_Speedometer', similarity_score: 0.73, estimated_duration_seconds: 40 },
];

const climateTests: TestCase[] = [
  { test_id: 'XRAY-1036', title: 'Climate control: restore temperature after ignition cycle', domain: 'Climate_Control', similarity_score: 0.86, estimated_duration_seconds: 90 },
  { test_id: 'XRAY-1037', title: 'Climate control: unavailable seat heating feedback', domain: 'Climate_Control', similarity_score: 0.69, estimated_duration_seconds: 60 },
];

export const demoScenarios: DemoScenario[] = [
  {
    id: 'speedometer',
    name: 'Speedometer signal scaling',
    change: 'A change adjusts the conversion of CAN signal 0x1A4 for the speedometer display.',
    defect: 'The displayed speed differs from the expected value at certain speeds.',
    result: {
      ranked_tests: speedTests,
      high_risk_tests: [speedTests[0]],
      total_hil_time_seconds: 85,
      full_suite_time_seconds: 600,
      hil_time_saved_seconds: 515,
      gap_tickets: [],
    },
  },
  {
    id: 'climate',
    name: 'Climate settings after restart',
    change: 'A change updates how climate settings are restored after an ignition cycle.',
    defect: 'The selected temperature is not restored after restarting the vehicle.',
    result: {
      ranked_tests: climateTests,
      high_risk_tests: [climateTests[0]],
      total_hil_time_seconds: 150,
      full_suite_time_seconds: 600,
      hil_time_saved_seconds: 450,
      gap_tickets: [],
    },
  },
  {
    id: 'parking-gap',
    name: 'Parking camera coverage gap',
    change: 'A change adds a parking camera overlay for an unfamiliar display configuration.',
    defect: 'The camera overlay is clipped on the new display layout.',
    result: {
      ranked_tests: [],
      high_risk_tests: [],
      total_hil_time_seconds: 0,
      full_suite_time_seconds: 600,
      hil_time_saved_seconds: 600,
      gap_tickets: [{
        domain: 'Parking_Assistance',
        similarity_max: 0.57,
        title: '[AUTO-GAP] Parking_Assistance: Regression Coverage',
        gap_reason: 'Illustrative example: no existing test text matched the change closely enough. Review the display configuration and add coverage if needed.',
        hil_bench_tags: ['ParkingCamera'],
      }],
    },
  },
];
