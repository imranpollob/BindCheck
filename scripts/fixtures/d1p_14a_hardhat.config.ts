/** D1P-14A execution-only overlay: mine reverting EDR transactions for receipts. */
import pinnedConfig from "./hardhat.config";

const base: any = pinnedConfig;

export default {
  ...base,
  networks: {
    ...base.networks,
    edr: {
      ...base.networks.edr,
      throwOnCallFailures: true,
      throwOnTransactionFailures: false,
    },
  },
};
