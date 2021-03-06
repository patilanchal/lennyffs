! len_mccylenvt.f90
! James Mithen
! j.mithen@surrey.ac.uk
!
! Fortran subroutine for executing Monte carlo cycles.  A cycle
! consists of nparfl attempted positional moves.  The Metropolis Monte
! Carlo algorithm is used.
!
! SUBROUTINES:
! len_executecyclesnvt - execute ncycles monte carlo cycles
!                        note xpos,ypos,zpos and etot are returned 

subroutine len_executecyclesnvt(xpos, ypos, zpos, ncycles, nsamp, rc,&
                                rcsq, vrc, vrc2, lboxx, lboxy, lboxz,&
                                eps4, maxdisp, npar, nsurf, zperiodic,&
                                sameseed, r6mult,r12mult, etot)
  ! execute ncycles MD cycles

  implicit none
  integer, parameter :: db = 8 !selected_real_kind(13)

  ! inputs
  integer, intent(in) :: ncycles, nsamp, npar, nsurf
  real(kind=db), intent(in) :: rc, rcsq, vrc, vrc2, lboxx, lboxy, lboxz
  real(kind=db), intent(in) :: eps4, maxdisp, r6mult, r12mult
  logical, intent(in) :: zperiodic, sameseed

  ! outputs
  real(kind=db), dimension(npar), intent(inout) :: xpos, ypos, zpos
  real(kind=db), intent(inout) :: etot

  !f2py intent(in) :: ncycles, nsamp, rc, rcsq, vrc, vrc2, lboxx, lboxy, lboxz, eps4
  !f2py intent(in) :: maxdisp, npar, nparsuf, zperiodic, sameseed, r6mult, r12mult
  !f2py intent(in,out) :: xpos, ypos, zpos, etot

  integer :: ipar, atmov, acmov, cy, it, nparfl
  real(kind=db) :: rsc, xposi, yposi, zposi, xposinew, yposinew,&
                   zposinew, eold, enew
  real(kind=db), dimension(3) :: rvec
  logical :: accept
  ! these are for cell lists
  integer :: ncelx, ncely, ncelz
  real(kind=db) :: rnx, rny, rnz
  integer, dimension(npar) :: ll
  integer, allocatable, dimension(:,:,:) :: hoc
  logical :: newlist
  
  ! initialize random number generator
  call init_random_seed(sameseed)

  ! get the number of cells and build the cell list
  call getnumcells(lboxx, lboxy, lboxz, rc, ncelx, ncely, ncelz)
  write(*,*) 'num cells', ncelx, ncely, ncelz
  allocate(hoc(ncelx, ncely, ncelx))
  call new_nlist(xpos, ypos, zpos, rc, lboxx, lboxy, lboxz, npar,&
                 ncelx, ncely, ncelz, ll, hoc, rnx, rny, rnz)

  ! counters for attempted and accepted moves
  atmov = 0
  acmov = 0
  nparfl = npar - nsurf

  write(*,*) 0,etot
  do cy = 1, ncycles
     do it = 1, nparfl
        atmov = atmov + 1

        ! pick a particle at random from fluid particles
        call random_number(rsc)
        ipar = int(rsc * nparfl) + 1 + nsurf
        xposi = xpos(ipar)
        yposi = ypos(ipar)
        zposi = zpos(ipar)

        ! find old energy
        call len_enlist(ll, hoc, ncelx, ncely, ncelz, ipar,&
                        xposi, yposi, zposi, xpos, ypos, zpos,&
                        rc, rcsq, lboxx, lboxy, lboxz, vrc, vrc2, npar,&
                        nsurf, zperiodic, r6mult, r12mult, eold)

        ! displace particle
        call random_number(rvec)
        xposinew = xposi + maxdisp * (rvec(1) - 0.5_db)
        yposinew = yposi + maxdisp * (rvec(2) - 0.5_db)
        zposinew = zposi + maxdisp * (rvec(3) - 0.5_db)

        if (zperiodic) then
           if (zposinew < 0.0_db) then
              zposinew = zposinew + lboxz
           else if (zposinew > lboxz) then
              zposinew = zposinew - lboxz
           end if
        end if
        
        ! if z not periodic, we will reject
        ! the move if z > lboxz (hard wall boundary)
        if (zposinew < lboxz .and. zposinew > 0.0_db) then
           
           ! periodic boundary conditions in x and y
           if (xposinew < 0.0_db) then
              xposinew = xposinew + lboxx
           else if (xposinew > lboxx) then
              xposinew = xposinew - lboxx
           end if
           if (yposinew < 0.0_db) then
              yposinew = yposinew + lboxy
           else if (yposinew > lboxy) then
              yposinew = yposinew - lboxy
           end if

           ! find new energy
           call len_enlist(ll, hoc, ncelx, ncely, ncelz, ipar,&
                           xposinew, yposinew, zposinew, xpos,&
                           ypos, zpos, rc, rcsq, lboxx, lboxy,&
                           lboxz, vrc, vrc2, npar, nsurf,&
                           zperiodic, r6mult, r12mult, enew)

           ! choose whether to accept the move or not
           accept = .True.
           if (enew > eold) then
              call random_number(rsc)
              if (exp((eold - enew) * eps4) < rsc) accept = .False.
           end if
           ! update positions if move accepted
           if (accept) then

              ! we don't rebuild the cell list by default.
              newlist = .False.

              ! check if the particle moved outside of its cell, if so
              ! we need the rebuild the cell list.  Note that the
              ! bracketed terms are in fact the cell number minus one,
              ! but there is clearly no point in adding the one here.
              if ((int(xpos(ipar) / rnx) .ne. int(xposinew / rnx)) .or.&
                  (int(ypos(ipar) / rny) .ne. int(yposinew / rny)) .or.&
                  (int(zpos(ipar) / rnz) .ne. int(zposinew / rnz))) then
                 newlist = .True.
              end if
              
              xpos(ipar) = xposinew
              ypos(ipar) = yposinew
              zpos(ipar) = zposinew
              etot = etot - eold + enew
              acmov = acmov + 1

              if (newlist) then
                 ! update the cell list
                 call new_nlist(xpos, ypos, zpos, rc, lboxx, lboxy, &
                                lboxz, npar, ncelx, ncely, ncelz, ll, &
                                hoc, rnx, rny, rnz)
              end if

           end if
        end if

     end do
     
     ! write out energy after every nsamp cycles
     if (mod(cy, nsamp) == 0) write(*, *) cy, etot
     
  end do

  ! write out acceptance ratio
  write(*,'("acceptance ratio", I7, I7, F7.3)') acmov, atmov, real(acmov) / atmov

end subroutine len_executecyclesnvt
