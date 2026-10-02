import { defineRailway, project } from "railway/iac";

/**
 * Grounded Studio does not deploy sensitive runtime services to Railway.
 *
 * WBRs, internal documents, recordings, transcripts, prompts, and artifacts
 * must remain on company-controlled/private infrastructure. Keeping this
 * project declaration with zero resources makes an old linked Railway project
 * converge to no application/storage runtime.
 */
export default defineRailway(() => {
  return project("grounded-studio-test", { resources: [] });
});
