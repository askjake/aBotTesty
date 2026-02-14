import axiosLibs from '@shared/ui/libs/axios.libs';
import {
  SetupVaultSchema,
  setupVaultValidator,
  UpdateVaultPasswordSchema,
  updateVaultPasswordValidator,
} from '@/validators/vault.validators';
import { pickKeys } from '@shared/ui/utils/common.utils';

import { SuccessResponseType } from '@shared/ui/types/common.types';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';

export const registerVaultService = async ({
  password,
}: SetupVaultSchema): Promise<SuccessResponseType> => {
  await setupVaultValidator.parseAsync({ password });

  const { data } = await axiosLibs.post('/vault/setup', {
    password,
  });
  return data;
};

export const updatePasswordVaultService = async ({
  oldPassword,
  newPassword,
}: UpdateVaultPasswordSchema): Promise<SuccessResponseType> => {
  await updateVaultPasswordValidator.parseAsync({ oldPassword, newPassword });

  const { data } = await axiosLibs.post('/vault/change-password', {
    oldPassword,
    newPassword,
  });
  return data;
};

export const enableVaultService = async ({
  password,
}: SetupVaultSchema): Promise<SuccessResponseType> => {
  await setupVaultValidator.parseAsync({ password });

  const { data } = await axiosLibs.post('/vault/verify', {
    password,
  });
  return data;
};

export const disableVaultService = async (): Promise<SuccessResponseType> => {
  const { data } = await axiosLibs.post('/vault/disable', {});
  return data;
};

export const checkVaultRegisteredService = async (
  incomingHeaders?: AxiosIncomingClientHeaders['incomingHeaders'],
): Promise<boolean> => {
  const {
    data: { exists = false },
  } = await axiosLibs.get('/vault/exists', {
    ...(incomingHeaders && {
      headers: {
        ...pickKeys({
          obj: incomingHeaders,
          keysToPick: ['x-auth-request-email', 'cookie'],
        }),
      },
    }),
  });
  return exists;
};

export const checkVaultStatusService = async (
  incomingHeaders?: AxiosIncomingClientHeaders['incomingHeaders'],
): Promise<boolean> => {
  const {
    data: { enabled = false },
  } = await axiosLibs.get('/vault/status', {
    ...(incomingHeaders && {
      headers: {
        ...pickKeys({
          obj: incomingHeaders,
          keysToPick: ['x-auth-request-email', 'cookie'],
        }),
      },
    }),
  });
  return enabled;
};

export const resetVaultModePasswordService =
  async (): Promise<SuccessResponseType> => {
    const {
      data: { success = false },
    } = await axiosLibs.post('/vault/reset-password');
    return success;
  };
